from abc import ABC, abstractmethod
from typing import List, Optional
from models.data_models.candle import Candle


class TechnicalIndicator(ABC):
    """Abstract base class for technical indicators."""
    
    def __init__(self, period: int = 14):
        self.period = period
    
    @abstractmethod
    def calculate(self, candles: List[Candle]) -> Optional[float]:
        """Calculate the indicator value for the given candles."""
        pass
    
    def validate_period(self, candles: List[Candle]) -> bool:
        """Validate that there are enough candles for the period."""
        return len(candles) >= self.period


class SimpleMovingAverage(TechnicalIndicator):
    """Simple Moving Average (SMA) indicator."""
    
    def calculate(self, candles: List[Candle]) -> Optional[float]:
        """Calculate SMA for the given candles."""
        if not self.validate_period(candles):
            return None
        
        # Get the last 'period' candles
        recent_candles = candles[-self.period:]
        
        # Calculate average of close prices
        total = sum(candle.close for candle in recent_candles)
        return total / self.period


class ExponentialMovingAverage(TechnicalIndicator):
    """Exponential Moving Average (EMA) indicator."""
    
    def __init__(self, period: int = 14):
        super().__init__(period)
        self.multiplier = 2 / (period + 1)
    
    def calculate(self, candles: List[Candle]) -> Optional[float]:
        """Calculate EMA for the given candles."""
        if not self.validate_period(candles):
            return None
        
        # Get the last 'period' candles
        recent_candles = candles[-self.period:]
        
        if len(recent_candles) == 0:
            return None
        
        # Start with SMA for the first calculation
        if len(recent_candles) == self.period:
            sma = sum(candle.close for candle in recent_candles) / self.period
            ema = sma
        else:
            # Use the first candle's close as initial EMA
            ema = recent_candles[0].close
        
        # Calculate EMA using the multiplier
        for candle in recent_candles[1:]:
            ema = (candle.close * self.multiplier) + (ema * (1 - self.multiplier))
        
        return ema


class RelativeStrengthIndex(TechnicalIndicator):
    """Relative Strength Index (RSI) indicator."""
    
    def __init__(self, period: int = 14):
        super().__init__(period)
    
    def calculate(self, candles: List[Candle]) -> Optional[float]:
        """Calculate RSI for the given candles."""
        if not self.validate_period(candles):
            return None
        
        # Get the last 'period + 1' candles to calculate price changes
        if len(candles) < self.period + 1:
            return None
        
        recent_candles = candles[-(self.period + 1):]
        
        # Calculate price changes
        gains = []
        losses = []
        
        for i in range(1, len(recent_candles)):
            change = recent_candles[i].close - recent_candles[i-1].close
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        # Calculate average gains and losses
        avg_gain = sum(gains) / self.period
        avg_loss = sum(losses) / self.period
        
        if avg_loss == 0:
            return 100
        
        # Calculate RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi


class BollingerBands(TechnicalIndicator):
    """Bollinger Bands indicator."""
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__(period)
        self.std_dev = std_dev
    
    def calculate(self, candles: List[Candle]) -> Optional[dict]:
        """Calculate Bollinger Bands for the given candles."""
        if not self.validate_period(candles):
            return None
        
        # Get the last 'period' candles
        recent_candles = candles[-self.period:]
        
        # Calculate SMA
        sma = sum(candle.close for candle in recent_candles) / self.period
        
        # Calculate standard deviation
        variance = sum((candle.close - sma) ** 2 for candle in recent_candles) / self.period
        std = variance ** 0.5
        
        # Calculate bands
        upper_band = sma + (self.std_dev * std)
        lower_band = sma - (self.std_dev * std)
        
        return {
            "upper": upper_band,
            "middle": sma,
            "lower": lower_band
        } 
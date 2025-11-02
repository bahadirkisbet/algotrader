"""
Simple Technical Indicators - Stateless batch calculation.

This module provides simple, stateless technical indicators for batch calculations.
These indicators take a list of candles and return a single value.

NOTE: For real-time/streaming indicator calculations with state management,
see data_center/jobs/technical_indicators/ which provides stateful indicators
that maintain state across individual candle updates.

Use these (modules/strategy/technical_indicators.py) when:
- You have a complete list of candles and need to calculate a single value
- You're doing batch/retrospective analysis
- You don't need to maintain state across updates

Use stateful indicators (data_center/jobs/technical_indicators/) when:
- You're processing candles one at a time in real-time
- You need to maintain calculation state
- You're building live trading systems
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from models.data_models.candle import Candle


class TechnicalIndicator(ABC):
    """Abstract base class for simple technical indicators."""

    def __init__(self, period: int = 14):
        self.period = period

    @abstractmethod
    def calculate(self, candles: List[Candle]) -> Optional[float]:
        """Calculate the indicator value for the given candles."""

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
        recent_candles = candles[-self.period :]

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
        recent_candles = candles[-self.period :]

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

    def calculate_batch(self, candles: List[Candle]) -> List[Optional[float]]:
        """
        Calculate EMA for all candles efficiently in a single pass.

        Returns a list of EMA values, where values before 'period' candles are None.
        This is much faster than calling calculate() repeatedly.

        Args:
            candles: List of all candles

        Returns:
            List of EMA values (None for indices < period)
        """
        if len(candles) == 0:
            return []

        ema_values: List[Optional[float]] = []

        # First period candles have no EMA
        for i in range(min(self.period, len(candles))):
            ema_values.append(None)

        if len(candles) < self.period:
            return ema_values

        # Calculate initial SMA for first period candles
        sma = sum(candle.close for candle in candles[: self.period]) / self.period
        ema = sma
        ema_values.append(ema)

        # Calculate EMA incrementally for remaining candles
        for i in range(self.period + 1, len(candles)):
            ema = (candles[i].close * self.multiplier) + (ema * (1 - self.multiplier))
            ema_values.append(ema)

        return ema_values


class RelativeStrengthIndex(TechnicalIndicator):
    """Relative Strength Index (RSI) indicator."""

    def calculate(self, candles: List[Candle]) -> Optional[float]:
        """Calculate RSI for the given candles."""
        if not self.validate_period(candles):
            return None

        # Get the last 'period + 1' candles to calculate price changes
        if len(candles) < self.period + 1:
            return None

        recent_candles = candles[-(self.period + 1) :]

        # Calculate price changes
        gains = []
        losses = []

        for i in range(1, len(recent_candles)):
            change = recent_candles[i].close - recent_candles[i - 1].close
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

    def calculate_batch(self, candles: List[Candle]) -> List[Optional[float]]:
        """
        Calculate RSI for all candles efficiently in a single pass using Wilder's smoothing.

        Returns a list of RSI values, where values before 'period+1' candles are None.
        This uses Wilder's smoothing method which is faster and more accurate than recalculating.

        Args:
            candles: List of all candles

        Returns:
            List of RSI values (None for indices < period+1)
        """
        if len(candles) == 0:
            return []

        rsi_values: List[Optional[float]] = []

        # First period+1 candles have no RSI (need period+1 for price changes)
        min_required = self.period + 1
        for i in range(min(min_required, len(candles))):
            rsi_values.append(None)

        if len(candles) < min_required:
            return rsi_values

        # Calculate initial average gain and loss for first period candles
        gains_sum = 0.0
        losses_sum = 0.0

        for i in range(1, min_required):
            change = candles[i].close - candles[i - 1].close
            if change > 0:
                gains_sum += change
            else:
                losses_sum += abs(change)

        avg_gain = gains_sum / self.period
        avg_loss = losses_sum / self.period

        # Calculate first RSI value
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        rsi_values.append(rsi)

        # Calculate RSI incrementally for remaining candles using Wilder's smoothing
        # Wilder's smoothing: new_avg = (prev_avg * (period - 1) + current_value) / period
        for i in range(min_required, len(candles)):
            change = candles[i].close - candles[i - 1].close

            if change > 0:
                current_gain = change
                current_loss = 0.0
            else:
                current_gain = 0.0
                current_loss = abs(change)

            # Wilder's smoothing method
            avg_gain = (avg_gain * (self.period - 1) + current_gain) / self.period
            avg_loss = (avg_loss * (self.period - 1) + current_loss) / self.period

            # Calculate RSI
            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))

            rsi_values.append(rsi)

        return rsi_values


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
        recent_candles = candles[-self.period :]

        # Calculate SMA
        sma = sum(candle.close for candle in recent_candles) / self.period

        # Calculate standard deviation
        variance = sum((candle.close - sma) ** 2 for candle in recent_candles) / self.period
        std = variance**0.5

        # Calculate bands
        upper_band = sma + (self.std_dev * std)
        lower_band = sma - (self.std_dev * std)

        return {"upper": upper_band, "middle": sma, "lower": lower_band}

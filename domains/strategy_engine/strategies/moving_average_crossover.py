"""
Moving Average Crossover Strategy.

This strategy generates buy/sell signals based on the crossover of two moving averages.
"""

from datetime import datetime
from typing import List, Optional

from .base_strategy import (
    BaseStrategy, TradingSignal, SignalType, SignalStrength, 
    StrategyState, MarketDataProvider
)
from models.data_models.candle import Candle


class MovingAverageCrossoverStrategy(BaseStrategy):
    """
    Moving Average Crossover Strategy.
    
    Generates signals when a fast moving average crosses above/below
    a slow moving average, indicating trend changes.
    """
    
    def __init__(self, name: str, symbols: List[str], fast_period: int = 10, slow_period: int = 20):
        self.fast_period = fast_period
        self.slow_period = slow_period
        
        # Set default parameters
        parameters = {
            "fast_period": fast_period,
            "slow_period": slow_period,
            "min_crossover_threshold": 0.001,  # Minimum price difference for signal
            "position_size_pct": 0.1,  # Use 10% of capital per trade
            "stop_loss_pct": 0.05,  # 5% stop loss
            "take_profit_pct": 0.15  # 15% take profit
        }
        
        super().__init__(name, symbols)
        self.set_parameters(parameters)
    
    def _initialize_strategy(self) -> None:
        """Initialize strategy-specific components."""
        # Initialize moving average values
        self.fast_ma_values = {}
        self.slow_ma_values = {}
        self.previous_fast_ma = {}
        self.previous_slow_ma = {}
    
    async def generate_signals(self, market_data: MarketDataProvider) -> List[TradingSignal]:
        """
        Generate trading signals based on moving average crossovers.
        
        Args:
            market_data: Market data provider interface
            
        Returns:
            List of trading signals
        """
        signals = []
        
        for symbol in self.symbols:
            # Get latest candle
            latest_candle = await market_data.get_latest_candle(symbol)
            if not latest_candle:
                continue
            
            # Calculate moving averages
            fast_ma = await self._calculate_fast_ma(symbol, market_data)
            slow_ma = await self._calculate_slow_ma(symbol, market_data)
            
            if fast_ma is None or slow_ma is None:
                continue
            
            # Update stored values
            self.fast_ma_values[symbol] = fast_ma
            self.slow_ma_values[symbol] = slow_ma
            
            # Check for crossover signals
            signal = await self._check_crossover_signal(symbol, latest_candle, fast_ma, slow_ma)
            if signal:
                signals.append(signal)
                self.add_signal(signal)
        
        return signals
    
    async def should_exit_position(self, market_data: MarketDataProvider) -> bool:
        """
        Determine if current position should be exited.
        
        Args:
            market_data: Market data provider interface
            
        Returns:
            True if position should be exited
        """
        if not self.is_position_open():
            return False
        
        # Check stop loss and take profit
        for symbol in self.symbols:
            latest_candle = await market_data.get_latest_candle(symbol)
            if not latest_candle:
                continue
            
            current_price = latest_candle.close
            
            if self.state.stop_loss and current_price <= self.state.stop_loss:
                return True
            
            if self.state.take_profit and current_price >= self.state.take_profit:
                return True
        
        return False
    
    async def _calculate_fast_ma(self, symbol: str, market_data: MarketDataProvider) -> Optional[float]:
        """Calculate fast moving average."""
        try:
            # Get historical data for calculation
            end_time = datetime.now()
            start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Get more data than needed to ensure we have enough
            candles = await market_data.get_historical_data(
                symbol, start_time, end_time, 
                limit=self.fast_period * 2
            )
            
            if len(candles) < self.fast_period:
                return None
            
            # Calculate simple moving average
            recent_candles = candles[-self.fast_period:]
            fast_ma = sum(c.close for c in recent_candles) / self.fast_period
            
            return fast_ma
            
        except Exception:
            return None
    
    async def _calculate_slow_ma(self, symbol: str, market_data: MarketDataProvider) -> Optional[float]:
        """Calculate slow moving average."""
        try:
            # Get historical data for calculation
            end_time = datetime.now()
            start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Get more data than needed to ensure we have enough
            candles = await market_data.get_historical_data(
                symbol, start_time, end_time, 
                limit=self.slow_period * 2
            )
            
            if len(candles) < self.slow_period:
                return None
            
            # Calculate simple moving average
            recent_candles = candles[-self.slow_period:]
            slow_ma = sum(c.close for c in recent_candles) / self.slow_period
            
            return slow_ma
            
        except Exception:
            return None
    
    async def _check_crossover_signal(
        self, 
        symbol: str, 
        candle: Candle, 
        fast_ma: float, 
        slow_ma: float
    ) -> Optional[TradingSignal]:
        """
        Check for moving average crossover signals.
        
        Args:
            symbol: Trading symbol
            candle: Latest candle
            fast_ma: Fast moving average value
            slow_ma: Slow moving average value
            
        Returns:
            Trading signal if crossover detected, None otherwise
        """
        current_price = candle.close
        timestamp = candle.datetime
        
        # Get previous values for crossover detection
        prev_fast = self.previous_fast_ma.get(symbol)
        prev_slow = self.previous_slow_ma.get(symbol)
        
        # Store current values for next iteration
        self.previous_fast_ma[symbol] = fast_ma
        self.previous_slow_ma[symbol] = slow_ma
        
        # Need previous values to detect crossover
        if prev_fast is None or prev_slow is None:
            return None
        
        # Check for bullish crossover (fast MA crosses above slow MA)
        if (prev_fast <= prev_slow and fast_ma > slow_ma and 
            abs(fast_ma - slow_ma) >= self.get_parameter("min_crossover_threshold")):
            
            # Calculate stop loss and take profit
            stop_loss = current_price * (1 - self.get_parameter("stop_loss_pct"))
            take_profit = current_price * (1 + self.get_parameter("take_profit_pct"))
            
            signal = TradingSignal(
                signal_type=SignalType.BUY,
                symbol=symbol,
                strength=SignalStrength.MEDIUM,
                timestamp=timestamp,
                price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata={
                    "fast_ma": fast_ma,
                    "slow_ma": slow_ma,
                    "crossover_type": "bullish"
                }
            )
            
            # Update strategy state
            self.update_state(
                current_position="long",
                entry_price=current_price,
                entry_time=timestamp,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            return signal
        
        # Check for bearish crossover (fast MA crosses below slow MA)
        elif (prev_fast >= prev_slow and fast_ma < slow_ma and 
              abs(fast_ma - slow_ma) >= self.get_parameter("min_crossover_threshold")):
            
            # For bearish crossover, we might want to close long positions
            if self.state.current_position == "long":
                signal = TradingSignal(
                    signal_type=SignalType.SELL,
                    symbol=symbol,
                    strength=SignalStrength.MEDIUM,
                    timestamp=timestamp,
                    price=current_price,
                    metadata={
                        "fast_ma": fast_ma,
                        "slow_ma": slow_ma,
                        "crossover_type": "bearish",
                        "action": "close_long"
                    }
                )
                
                # Update strategy state
                self.update_state(
                    current_position=None,
                    entry_price=None,
                    entry_time=None,
                    stop_loss=None,
                    take_profit=None
                )
                
                return signal
        
        return None
    
    def get_strategy_info(self) -> dict:
        """Get detailed strategy information."""
        return {
            "name": self.name,
            "type": "Moving Average Crossover",
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "parameters": self.parameters,
            "current_state": self.state,
            "fast_ma_values": self.fast_ma_values,
            "slow_ma_values": self.slow_ma_values
        } 
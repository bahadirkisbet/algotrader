"""
Base strategy class for algorithmic trading strategies.

This module provides a clean foundation for implementing trading strategies
that can work in both simulation and live trading environments.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Protocol
from dataclasses import dataclass, field
from enum import Enum

from models.data_models.candle import Candle
from domains.trading.exchanges.base_exchange import OrderRequest


class SignalType(Enum):
    """Trading signal types."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


class SignalStrength(Enum):
    """Signal strength levels."""
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"


@dataclass
class TradingSignal:
    """Trading signal data structure."""
    signal_type: SignalType
    symbol: str
    strength: SignalStrength
    timestamp: datetime
    price: float
    quantity: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class StrategyState:
    """Strategy execution state."""
    is_active: bool = True
    current_position: Optional[str] = None  # 'long', 'short', or None
    entry_price: Optional[float] = None
    entry_time: Optional[datetime] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: Dict = field(default_factory=dict)


class MarketDataProvider(Protocol):
    """Protocol for market data providers."""
    async def get_latest_candle(self, symbol: str) -> Optional[Candle]:
        """Get the latest candle for a symbol."""
        ...
    
    async def get_historical_data(
        self, 
        symbol: str, 
        start_time: datetime, 
        end_time: datetime,
        limit: Optional[int] = None
    ) -> List[Candle]:
        """Get historical data for a symbol."""
        ...
    
    async def get_indicator_value(self, symbol: str, indicator_name: str) -> Optional[float]:
        """Get calculated indicator value."""
        ...


class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies.
    
    This class provides a clean interface for implementing strategies
    that can work in both simulation and live trading environments.
    """
    
    def __init__(self, name: str, symbols: List[str]):
        self.name = name
        self.symbols = symbols
        self.state = StrategyState()
        self.parameters: Dict = {}
        self.indicators: Dict[str, float] = {}
        self.signal_history: List[TradingSignal] = []
        self.performance_metrics: Dict = {}
        
        # Initialize strategy
        self._initialize_strategy()
    
    def _initialize_strategy(self) -> None:
        """Initialize strategy-specific components."""
        # Override in subclasses
        pass
    
    @abstractmethod
    async def generate_signals(self, market_data: MarketDataProvider) -> List[TradingSignal]:
        """
        Generate trading signals based on market data.
        
        Args:
            market_data: Market data provider interface
            
        Returns:
            List of trading signals
        """
        pass
    
    @abstractmethod
    async def should_exit_position(self, market_data: MarketDataProvider) -> bool:
        """
        Determine if current position should be exited.
        
        Args:
            market_data: Market data provider interface
            
        Returns:
            True if position should be exited
        """
        pass
    
    def set_parameters(self, parameters: Dict) -> None:
        """Set strategy parameters."""
        self.parameters.update(parameters)
    
    def get_parameter(self, key: str, default=None):
        """Get a strategy parameter."""
        return self.parameters.get(key, default)
    
    def update_indicator(self, name: str, value: float) -> None:
        """Update indicator value."""
        self.indicators[name] = value
    
    def get_indicator(self, name: str) -> Optional[float]:
        """Get indicator value."""
        return self.indicators.get(name)
    
    def add_signal(self, signal: TradingSignal) -> None:
        """Add signal to history."""
        self.signal_history.append(signal)
    
    def get_recent_signals(self, count: int = 10) -> List[TradingSignal]:
        """Get recent trading signals."""
        return self.signal_history[-count:] if self.signal_history else []
    
    def update_state(self, **kwargs) -> None:
        """Update strategy state."""
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
    
    def is_position_open(self) -> bool:
        """Check if strategy has an open position."""
        return self.state.current_position is not None
    
    def get_position_info(self) -> Dict:
        """Get current position information."""
        return {
            "position": self.state.current_position,
            "entry_price": self.state.entry_price,
            "entry_time": self.state.entry_time,
            "stop_loss": self.state.stop_loss,
            "take_profit": self.state.take_profit
        }
    
    def calculate_position_size(self, capital: float, risk_per_trade: float = 0.02) -> float:
        """
        Calculate position size based on risk management rules.
        
        Args:
            capital: Available capital
            risk_per_trade: Risk per trade as fraction of capital
            
        Returns:
            Position size in base currency
        """
        if not self.state.stop_loss or not self.state.entry_price:
            return 0.0
        
        risk_amount = capital * risk_per_trade
        price_risk = abs(self.state.entry_price - self.state.stop_loss)
        
        if price_risk == 0:
            return 0.0
        
        return risk_amount / price_risk
    
    def create_order_request(self, signal: TradingSignal, quantity: float) -> OrderRequest:
        """
        Create order request from trading signal.
        
        Args:
            signal: Trading signal
            quantity: Order quantity
            
        Returns:
            Order request
        """
        return OrderRequest(
            symbol=signal.symbol,
            side=signal.signal_type.value,
            order_type="market",  # Default to market orders
            quantity=quantity,
            price=signal.price
        )
    
    def get_performance_summary(self) -> Dict:
        """Get strategy performance summary."""
        total_signals = len(self.signal_history)
        buy_signals = len([s for s in self.signal_history if s.signal_type == SignalType.BUY])
        sell_signals = len([s for s in self.signal_history if s.signal_type == SignalType.SELL])
        
        return {
            "name": self.name,
            "total_signals": total_signals,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "current_position": self.state.current_position,
            "indicators": self.indicators.copy(),
            "parameters": self.parameters.copy()
        }
    
    def reset(self) -> None:
        """Reset strategy state for new simulation."""
        self.state = StrategyState()
        self.signal_history.clear()
        self.performance_metrics.clear()
        self.indicators.clear()
    
    def __str__(self) -> str:
        """String representation of the strategy."""
        return f"{self.name}(symbols={self.symbols}, active={self.state.is_active})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"{self.__class__.__name__}(name='{self.name}', "
                f"symbols={self.symbols}, state={self.state})") 
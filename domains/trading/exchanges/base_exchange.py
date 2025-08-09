"""
Base exchange interface for trading operations.

This module provides a clean abstraction for exchange interactions,
ensuring easy switching between simulation and live trading.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Protocol
from dataclasses import dataclass

from models.data_models.candle import Candle
from models.time_models import Interval


@dataclass
class OrderRequest:
    """Order request data structure."""
    symbol: str
    side: str  # 'buy' or 'sell'
    order_type: str  # 'market', 'limit', 'stop'
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = 'GTC'  # Good Till Canceled


@dataclass
class OrderResponse:
    """Order response data structure."""
    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float]
    status: str
    timestamp: datetime
    filled_quantity: float = 0.0
    average_price: Optional[float] = None


@dataclass
class Position:
    """Position data structure."""
    symbol: str
    side: str  # 'long' or 'short'
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    timestamp: datetime


class MarketDataCallback(Protocol):
    """Protocol for market data callbacks."""
    async def on_candle(self, candle: Candle) -> None:
        """Called when new candle data arrives."""
        ...

    async def on_trade(self, trade_data: Dict) -> None:
        """Called when new trade data arrives."""
        ...


class BaseExchange(ABC):
    """
    Abstract base class for exchange implementations.
    
    This class provides a clean interface that can be implemented
    by both real exchanges and simulation engines.
    """
    
    def __init__(self, name: str, is_simulation: bool = False):
        self.name = name
        self.is_simulation = is_simulation
        self.connected = False
        self.market_data_callback: Optional[MarketDataCallback] = None
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the exchange."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the exchange."""
        pass
    
    @abstractmethod
    async def get_account_info(self) -> Dict:
        """Get account information."""
        pass
    
    @abstractmethod
    async def get_symbols(self) -> List[str]:
        """Get available trading symbols."""
        pass
    
    @abstractmethod
    async def get_historical_data(
        self, 
        symbol: str, 
        interval: Interval, 
        start_time: datetime, 
        end_time: datetime,
        limit: Optional[int] = None
    ) -> List[Candle]:
        """Get historical market data."""
        pass
    
    @abstractmethod
    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Place a new order."""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order."""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str, symbol: str) -> OrderResponse:
        """Get the status of an order."""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get current positions."""
        pass
    
    @abstractmethod
    async def get_balance(self) -> Dict[str, float]:
        """Get account balance."""
        pass
    
    def set_market_data_callback(self, callback: MarketDataCallback) -> None:
        """Set the market data callback."""
        self.market_data_callback = callback
    
    async def subscribe_to_market_data(self, symbols: List[str], interval: Interval) -> None:
        """Subscribe to market data for specified symbols."""
        if not self.market_data_callback:
            raise ValueError("Market data callback not set")
        # Implementation specific to each exchange
    
    async def unsubscribe_from_market_data(self, symbols: List[str], interval: Interval) -> None:
        """Unsubscribe from market data for specified symbols."""
        # Implementation specific to each exchange
    
    def is_connected(self) -> bool:
        """Check if the exchange is connected."""
        return self.connected
    
    def get_name(self) -> str:
        """Get the exchange name."""
        return self.name 
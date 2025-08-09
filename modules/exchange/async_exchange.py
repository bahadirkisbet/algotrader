import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime

from models.exchange_type import ExchangeType
from models.data_models.candle import Candle
from models.time_models import Interval


class AsyncExchange(ABC):
    """Abstract base class for async exchange implementations."""

    def __init__(self, exchange_type: ExchangeType):
        self.exchange_type = exchange_type
        self.exchange_name = self.__class__.__name__
        self.logger: Optional[logging.Logger] = None
        self.__initialized__ = False
        self.__candle_callbacks__: List[Callable[[Candle], None]] = []
        self.__websocket_subscriptions__: Dict[str, Any] = {}
        self.__lock__ = asyncio.Lock()

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the exchange connection and setup."""
        pass

    @abstractmethod
    async def get_exchange_name(self) -> str:
        """Get the name of the exchange."""
        pass

    @abstractmethod
    async def fetch_product_list(self) -> List[str]:
        """Fetch the list of available trading products."""
        pass

    @abstractmethod
    async def fetch_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: Interval
    ) -> List[Candle]:
        """Fetch historical data for a symbol."""
        pass

    @abstractmethod
    async def subscribe_to_websocket(
        self,
        symbols: List[str],
        interval: Interval
    ) -> bool:
        """Subscribe to real-time data via WebSocket."""
        pass

    @abstractmethod
    async def unsubscribe_from_websocket(self) -> bool:
        """Unsubscribe from WebSocket data."""
        pass

    def register_candle_callback(self, callback: Callable[[Candle], None]) -> None:
        """Register a callback for candle data updates."""
        if callback not in self.__candle_callbacks__:
            self.__candle_callbacks__.append(callback)
            if self.logger:
                self.logger.debug(f"Registered candle callback: {callback.__name__}")

    def unregister_candle_callback(self, callback: Callable[[Candle], None]) -> None:
        """Unregister a candle callback."""
        if callback in self.__candle_callbacks__:
            self.__candle_callbacks__.remove(callback)
            if self.logger:
                self.logger.debug(f"Unregistered candle callback: {callback.__name__}")

    async def _notify_candle_callbacks(self, candle: Candle) -> None:
        """Notify all registered candle callbacks."""
        if not self.__candle_callbacks__:
            return

        # Create tasks for all callbacks to run concurrently
        tasks = []
        for callback in self.__candle_callbacks__:
            try:
                if asyncio.iscoroutinefunction(callback):
                    task = asyncio.create_task(callback(candle))
                else:
                    # Run synchronous callbacks in thread pool
                    loop = asyncio.get_event_loop()
                    task = loop.run_in_executor(None, callback, candle)
                tasks.append(task)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error creating callback task: {e}")

        # Wait for all callbacks to complete
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error in candle callbacks: {e}")

    async def get_exchange_info(self) -> Dict[str, Any]:
        """Get general information about the exchange."""
        return {
            "name": self.exchange_name,
            "type": self.exchange_type.value,
            "initialized": self.__initialized__,
            "active_subscriptions": len(self.__websocket_subscriptions__),
            "registered_callbacks": len(self.__candle_callbacks__)
        }

    async def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific symbol."""
        try:
            # This is a base implementation - subclasses should override
            return {
                "symbol": symbol,
                "exchange": self.exchange_name,
                "type": self.exchange_type.value
            }
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting symbol info for {symbol}: {e}")
            return None

    async def test_connection(self) -> bool:
        """Test the connection to the exchange."""
        try:
            # Basic connection test - subclasses should implement specific logic
            await self.fetch_product_list()
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Connection test failed: {e}")
            return False

    async def close(self) -> None:
        """Close the exchange connection and cleanup."""
        try:
            # Unsubscribe from all websockets
            await self.unsubscribe_from_websocket()
            
            # Clear callbacks
            self.__candle_callbacks__.clear()
            
            # Mark as not initialized
            self.__initialized__ = False
            
            if self.logger:
                self.logger.info(f"Exchange {self.exchange_name} closed")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error closing exchange: {e}")

    def is_initialized(self) -> bool:
        """Check if the exchange is initialized."""
        return self.__initialized__

    def get_callback_count(self) -> int:
        """Get the number of registered callbacks."""
        return len(self.__candle_callbacks__)

    def get_subscription_count(self) -> int:
        """Get the number of active WebSocket subscriptions."""
        return len(self.__websocket_subscriptions__)

    async def _set_initialized(self, value: bool) -> None:
        """Set the initialized state (protected method)."""
        self.__initialized__ = value

    def set_logger(self, logger: logging.Logger) -> None:
        """Set the logger for this exchange."""
        self.logger = logger 
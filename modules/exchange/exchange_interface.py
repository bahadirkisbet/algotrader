import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from models.data_models.candle import Candle
from models.exchange_type import ExchangeType
from models.time_models import Interval


class ExchangeInterface(ABC):
    """Abstract base class for exchange implementations."""

    def __init__(self, exchange_type: ExchangeType):
        self.exchange_type = exchange_type
        self.exchange_name = self.__class__.__name__
        self.logger: Optional[logging.Logger] = None
        self.is_initialized = False
        self.candle_callbacks: List[Callable[[Candle], None]] = []
        self.websocket_subscriptions: Dict[str, Any] = {}
        self.lock = asyncio.Lock()

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
        if callback not in self.candle_callbacks:
            self.candle_callbacks.append(callback)
            if self.logger:
                self.logger.debug(f"Registered candle callback: {callback.__name__}")

    def unregister_candle_callback(self, callback: Callable[[Candle], None]) -> None:
        """Unregister a candle callback."""
        if callback in self.candle_callbacks:
            self.candle_callbacks.remove(callback)
            if self.logger:
                self.logger.debug(f"Unregistered candle callback: {callback.__name__}")

    async def notify_candle_callbacks(self, candle: Candle) -> None:
        """Notify all registered candle callbacks."""
        if not self.candle_callbacks:
            return

        # Create tasks for all callbacks to run concurrently
        tasks = []
        for callback in self.candle_callbacks:
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
                    self.logger.error(f"Error in callback execution: {e}")

    @abstractmethod
    async def get_exchange_info(self) -> Dict[str, Any]:
        """Get general exchange information."""
        pass

    @abstractmethod
    async def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific trading symbol."""
        pass

    async def test_connection(self) -> bool:
        """Test the connection to the exchange."""
        try:
            if not self.is_initialized:
                return False
            
            # Try to fetch basic exchange info
            await self.get_exchange_info()
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Connection test failed: {e}")
            return False

    async def close(self) -> None:
        """Close the exchange connection and cleanup."""
        try:
            if self.logger:
                self.logger.info(f"Closing {self.exchange_name} connection...")
            
            # Unsubscribe from all WebSocket streams
            await self.unsubscribe_from_websocket()
            
            # Clear callbacks
            self.candle_callbacks.clear()
            
            # Clear subscriptions
            self.websocket_subscriptions.clear()
            
            self.is_initialized = False
            
            if self.logger:
                self.logger.info(f"{self.exchange_name} connection closed successfully")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error closing {self.exchange_name} connection: {e}")

    def is_initialized(self) -> bool:
        """Check if the exchange is initialized."""
        return self.is_initialized

    def get_callback_count(self) -> int:
        """Get the number of registered callbacks."""
        return len(self.candle_callbacks)

    def get_subscription_count(self) -> int:
        """Get the number of active WebSocket subscriptions."""
        return len(self.websocket_subscriptions)

    async def set_initialized(self, value: bool) -> None:
        """Set the initialization status."""
        async with self.lock:
            self.is_initialized = value

    def set_logger(self, logger: logging.Logger) -> None:
        """Set the logger for this exchange."""
        self.logger = logger 
"""
Base ExchangeWebSocket class for WebSocket operations.

This module provides the abstract base class for exchange WebSocket implementations
that handle real-time data streaming.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from models.data_models.candle import Candle
from models.time_models import Interval


class ExchangeWebSocket(ABC):
    """
    Abstract base class for exchange WebSocket operations.

    This class handles WebSocket connections and real-time data streaming,
    following the Single Responsibility Principle by separating WebSocket
    concerns from REST API operations.
    """

    def __init__(self, websocket_url: str):
        """
        Initialize the WebSocket connection manager.

        Args:
            websocket_url: Base URL for WebSocket connections
        """
        self.websocket_url = websocket_url
        self.logger: Optional[logging.Logger] = None
        self.is_connected = False

        # Callback management
        self.candle_callbacks: List[Callable[[Candle], None]] = []

        # Subscription tracking
        self.subscriptions: Dict[str, Any] = {}

        # WebSocket state
        self.websocket: Optional[Any] = None
        self.websocket_task: Optional[asyncio.Task] = None

        # Thread safety
        self.lock = asyncio.Lock()

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish WebSocket connection.

        Returns:
            True if connection successful, False otherwise
        """

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Close WebSocket connection.

        Returns:
            True if disconnection successful, False otherwise
        """

    @abstractmethod
    async def subscribe(self, symbols: List[str], interval: Interval) -> bool:
        """
        Subscribe to real-time data streams for given symbols.

        Args:
            symbols: List of trading pair symbols
            interval: Time interval for candle data

        Returns:
            True if subscription successful, False otherwise
        """

    @abstractmethod
    async def unsubscribe(self, symbols: List[str], interval: Interval) -> bool:
        """
        Unsubscribe from data streams.

        Args:
            symbols: List of trading pair symbols to unsubscribe from
            interval: Time interval for candle data

        Returns:
            True if unsubscription successful, False otherwise
        """

    @abstractmethod
    async def _handle_message(self, message: Any) -> None:
        """
        Handle incoming WebSocket messages.

        This method should parse messages and convert them to Candle objects,
        then notify registered callbacks.

        Args:
            message: Raw WebSocket message
        """

    @abstractmethod
    def _prepare_subscribe_message(self, symbol: str, interval: Interval) -> Dict[str, Any]:
        """
        Prepare exchange-specific subscription message.

        Args:
            symbol: Trading pair symbol
            interval: Time interval for candles

        Returns:
            Subscription message as dictionary
        """

    @abstractmethod
    def _prepare_unsubscribe_message(self, symbol: str, interval: Interval) -> Dict[str, Any]:
        """
        Prepare exchange-specific unsubscription message.

        Args:
            symbol: Trading pair symbol
            interval: Time interval for candles

        Returns:
            Unsubscription message as dictionary
        """

    def register_candle_callback(self, callback: Callable[[Candle], None]) -> None:
        """
        Register a callback for candle data updates.

        Args:
            callback: Function to call when new candle data arrives
        """
        if callback not in self.candle_callbacks:
            self.candle_callbacks.append(callback)
            if self.logger:
                self.logger.debug("Registered candle callback: %s", callback.__name__)

    def unregister_candle_callback(self, callback: Callable[[Candle], None]) -> None:
        """
        Unregister a candle callback.

        Args:
            callback: Function to remove from callbacks
        """
        if callback in self.candle_callbacks:
            self.candle_callbacks.remove(callback)
            if self.logger:
                self.logger.debug("Unregistered candle callback: %s", callback.__name__)

    async def notify_candle_callbacks(self, candle: Candle) -> None:
        """
        Notify all registered callbacks with new candle data.

        Args:
            candle: New candle data to broadcast
        """
        if not self.candle_callbacks:
            return

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
            except (RuntimeError, TypeError, ValueError) as e:
                if self.logger:
                    self.logger.error("Error creating callback task: %s", e)

        if tasks:
            # gather with return_exceptions=True returns exceptions instead of raising
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_callback_count(self) -> int:
        """
        Get the number of registered callbacks.

        Returns:
            Number of registered callbacks
        """
        return len(self.candle_callbacks)

    def get_subscription_count(self) -> int:
        """
        Get the number of active subscriptions.

        Returns:
            Number of active subscriptions
        """
        return len(self.subscriptions)

    async def set_connected(self, value: bool) -> None:
        """
        Set connection status thread-safely.

        Args:
            value: Connection status
        """
        async with self.lock:
            self.is_connected = value

    def set_logger(self, logger: logging.Logger) -> None:
        """
        Set the logger for this WebSocket manager.

        Args:
            logger: Logger instance to use
        """
        self.logger = logger

    async def cleanup(self) -> None:
        """
        Clean up WebSocket resources.

        This method should be called when done using the WebSocket to properly
        cleanup resources.
        """
        try:
            if self.logger:
                self.logger.info("Cleaning up WebSocket resources...")

            # Disconnect if still connected
            if self.is_connected:
                await self.disconnect()

            # Clear callbacks
            self.candle_callbacks.clear()

            # Clear subscriptions
            self.subscriptions.clear()

            if self.logger:
                self.logger.info("WebSocket cleanup completed")

        except (RuntimeError, asyncio.CancelledError) as e:
            if self.logger:
                self.logger.error("Error during WebSocket cleanup: %s", e)

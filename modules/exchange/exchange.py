"""
Base Exchange class for REST API operations.

This module provides the abstract base class for exchange implementations
that handle REST API operations like fetching products, historical data, etc.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from models.data_models.candle import Candle
from models.exchange_info import ExchangeInfo
from models.exchange_type import ExchangeType
from models.sorting_option import SortingOption
from models.time_models import Interval


class Exchange(ABC):
    """
    Abstract base class for exchange REST API operations.

    This class handles initialization of common exchange properties and defines
    the interface for REST API operations following the Single Responsibility Principle.
    """

    def __init__(self, exchange_type: ExchangeType):
        """
        Initialize the exchange with common properties.

        Args:
            exchange_type: The type of exchange (SPOT, FUTURES, etc.)
        """
        self.exchange_type = exchange_type
        self.exchange_name = self.__class__.__name__
        self.logger: Optional[logging.Logger] = None
        self.is_initialized = False
        self.lock = asyncio.Lock()

        # Exchange configuration
        self.api_url: str = ""
        self.api_endpoints: Dict[str, str] = {}
        self.first_data_date: Optional[datetime] = None

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the exchange connection and setup.

        This method should be called before using any other exchange methods.
        It's responsible for setting up HTTP sessions, validating credentials, etc.
        """

    @abstractmethod
    async def get_exchange_name(self) -> str:
        """
        Get the name of the exchange.

        Returns:
            Exchange name as string (e.g., "Binance", "Coinbase")
        """

    @abstractmethod
    async def fetch_product_list(
        self, sorting_option: Optional[SortingOption] = None, limit: int = -1
    ) -> List[str]:
        """
        Fetch the list of available trading products.

        Args:
            sorting_option: Optional sorting configuration
            limit: Maximum number of products to return (-1 for all)

        Returns:
            List of trading pair symbols
        """

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: Interval,
    ) -> List[Candle]:
        """
        Fetch OHLCV (Open, High, Low, Close, Volume) data.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Time interval for candles

        Returns:
            List of Candle objects
        """

    @abstractmethod
    async def fetch_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: Interval,
    ) -> List[Candle]:
        """
        Fetch historical candle data for a symbol.

        This is an alias/wrapper for fetch_ohlcv for better API clarity.

        Args:
            symbol: Trading pair symbol
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Time interval for candles

        Returns:
            List of Candle objects
        """

    @abstractmethod
    async def get_exchange_info(self) -> ExchangeInfo:
        """
        Get general exchange information.

        Returns:
            ExchangeInfo object with exchange metadata
        """

    @abstractmethod
    async def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific trading symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            Dictionary with symbol information or None if not found
        """

    async def test_connection(self) -> bool:
        """
        Test the connection to the exchange.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            if not self.is_initialized:
                return False

            await self.get_exchange_info()
            return True

        except Exception as e:
            if self.logger:
                self.logger.error("Connection test failed: %s", e)
            return False

    async def close(self) -> None:
        """
        Close the exchange connection and cleanup resources.

        This method should be called when done using the exchange to properly
        cleanup resources like HTTP sessions.
        """
        try:
            if self.logger:
                self.logger.info("Closing %s connection...", self.exchange_name)

            self.is_initialized = False

            if self.logger:
                self.logger.info("%s connection closed successfully", self.exchange_name)

        except Exception as e:
            if self.logger:
                self.logger.error("Error closing %s connection: %s", self.exchange_name, e)

    async def set_initialized(self, value: bool) -> None:
        """
        Set the initialization status thread-safely.

        Args:
            value: Initialization status
        """
        async with self.lock:
            self.is_initialized = value

    def set_logger(self, logger: logging.Logger) -> None:
        """
        Set the logger for this exchange.

        Args:
            logger: Logger instance to use
        """
        self.logger = logger

    @abstractmethod
    def interval_to_granularity(self, interval: Interval) -> str:
        """
        Convert internal interval representation to exchange-specific format.

        Args:
            interval: Internal interval enum

        Returns:
            Exchange-specific interval string (e.g., "1m", "1h")
        """

    @abstractmethod
    def get_max_candle_limit(self) -> int:
        """
        Get the maximum number of candles that can be fetched in a single request.

        Returns:
            Maximum candle limit
        """

    @abstractmethod
    def convert_datetime_to_exchange_timestamp(self, dt: datetime) -> str:
        """
        Convert datetime to exchange-specific timestamp format.

        Args:
            dt: Datetime object to convert

        Returns:
            Exchange-specific timestamp string
        """

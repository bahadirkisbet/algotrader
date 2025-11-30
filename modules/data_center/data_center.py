"""
Data Center for managing market data and technical indicators.

This is the central provider for all market data (candles and indicators)
used by the strategy manager. It supports both backfill (historical) and
production (real-time) modes.
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional

from modules.archive.archive_manager import ArchiveManager
from modules.config import config
from modules.data_center.symbol_collection import SymbolCollection
from modules.exchange.exchange import Exchange
from modules.exchange.exchange_factory import ExchangeFactory
from modules.exchange.exchange_websocket import ExchangeWebSocket
from modules.log import LogManager
from modules.model.candle import Candle


class DataCenter:
    """
    Central data center for market data and indicators.

    Features:
    - Supports backfill mode (historical data replay)
    - Supports production mode (real-time WebSocket)
    - Automatically creates all available indicators
    - Provides normalized data access for strategies
    """

    def __init__(self):
        """Initialize the data center."""
        self.logger = LogManager.get_logger()
        archive_section = config.get("archive", {})
        self.archive_manager = ArchiveManager(
            archive_folder=archive_section.get("archive_folder", ".cache"),
            default_encoding=archive_section.get("default_encoding", "utf-8"),
        )

        # Exchange instances
        self.exchange: Optional[Exchange] = None
        self.websocket: Optional[ExchangeWebSocket] = None

        self._loop_task: Optional[asyncio.Task] = None

        # Symbol configuration
        self.symbol_collections: Dict[str, SymbolCollection] = {}

    def _initialize_symbol_collections(self) -> None:
        """Initialize the symbol collections."""
        for symbol in config.get("symbols", []):
            pair = symbol.get("pair")
            interval = symbol.get("interval")
            indicators = symbol.get("indicators")
            self.symbol_collections[f"{pair}@{interval}"] = SymbolCollection(
                symbol=pair, interval=interval, indicators=indicators
            )

    async def initialize(self) -> None:
        """Initialize the data center."""
        try:
            self.logger.info("Initializing DataCenter...")

            self._initialize_symbol_collections()

            self.logger.info("DataCenter initialized successfully")

        except Exception as e:
            self.logger.error("Failed to initialize DataCenter: %s", e)
            raise

    def _request_candle_callback(
        self, symbol: str, index: int = 0, reverse: bool = False
    ) -> Optional[Candle]:
        """
        Callback for IndicatorManager to request candles.

        This provides normalized access to historical candles.
        """
        if symbol not in self.symbol_collections:
            return None

        symbol_collection = self.symbol_collections[symbol]
        return symbol_collection.get_candle(index, reverse)

    async def start(self) -> None:
        """Start the data center."""

        try:
            self.logger.info("Starting DataCenter...")

            # Start processing task
            self._loop_task = asyncio.create_task(self._processing_loop())

            self.logger.info("DataCenter started successfully")

        except Exception as e:
            self.logger.error("Failed to start DataCenter: %s", e)
            raise

    async def _processing_loop(self) -> None:
        """
        Start production mode with WebSocket.
        if end date or start date is not defined, this is going to be production
        otherwise it will be backtest mode.

        """
        trading_section = config.get("trading", {})
        start_date = trading_section.get("start_date")
        end_date = trading_section.get("end_date", datetime.now())
        provider = None
        if start_date and end_date:
            provider = await self._initialize_backtest_mode(start_date, end_date)
        else:
            raise NotImplementedError("Production mode is not implemented")

        await provider.start(self._on_candle_received, self.symbol_collections.keys())

    async def _initialize_backtest_mode(
        self, start_date: datetime, end_date: datetime
    ) -> None:
        """
        Initialize backtest mode.
        """

        exchange_code = config.get("exchange", {}).get("code")
        if not exchange_code:
            raise ValueError("Exchange code is not set")
        self.exchange = await ExchangeFactory.create_exchange(exchange_code)
        await self.exchange.initialize(self._on_candle_received)
        await self.exchange.fetch_historical_data(
            [x.get_symbol_code() for x in self.symbol_collections.values()],
            start_date,
            end_date,
            Interval.MINUTE_1,
        )
        return self.exchange

    async def _initialize_production_mode(self) -> None:
        """
        Initialize production mode.
        """
        await self.websocket.connect()
        return self.websocket

    async def _on_candle_received(self, candle: Candle) -> None:
        """
        Handle new candle from exchange (backfill or production).

        This normalizes the candle and calculates all indicators.
        """
        try:
            # Normalize candle (ensure it's using the standard Candle model)

            # Store candle
            symbol = candle.symbol
            if symbol not in self.symbol_collections:
                self.logger.error("Symbol %s not found in symbol collections", symbol)
                return

            symbol_collection = self.symbol_collections[symbol]
            symbol_collection.add_candle(candle)

            self.logger.debug("Processed candle for %s: %s", symbol, candle)

        except Exception as e:
            self.logger.error("Error processing candle: %s", e)

    async def get_candle(
        self, symbol: str, index: int = 0, reverse: bool = False
    ) -> Optional[Candle]:
        """
        Get a candle by index.

        Args:
            symbol: Trading pair symbol
            index: Index offset
            reverse: If True, index from most recent (0 = latest)

        Returns:
            Candle or None if not found
        """
        return self._request_candle_callback(symbol, index, reverse)

    async def close(self) -> None:
        """Close the data center."""
        if self._loop_task:
            self._loop_task.cancel()
        if self.websocket:
            await self.websocket.close()
        self.logger.info("DataCenter closed successfully")

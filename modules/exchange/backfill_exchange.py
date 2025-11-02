"""
Backfill Exchange for historical data replay.

This exchange mock behaves like binance_data_ingestor.py - it uses archived data
and fetches from Binance Vision if data doesn't exist locally.
"""

import asyncio
from datetime import datetime
from typing import Callable, Dict, List, Optional

from models.data_models.candle import Candle
from models.time_models import Interval
from modules.archive.archive_manager import ArchiveManager
from modules.config.config_manager import ConfigManager
from modules.exchange.exchange import Exchange
from modules.exchange.exchange_factory import ExchangeFactory
from modules.log import LogManager


class BackfillExchange:
    """
    Mock exchange for backfill mode that uses archived data.

    If data doesn't exist in archive, it fetches from Binance Vision API
    (similar to binance_data_ingestor.py behavior).
    """

    def __init__(self, config_file: str = "config.ini"):
        """Initialize backfill exchange."""
        self.logger = LogManager.get_logger(ConfigManager.get_config())
        self.archive_manager = ArchiveManager(config_file)
        self.real_exchange: Optional[Exchange] = None
        self.candle_callbacks: List[Callable[[Candle], None]] = []

        # Store candles by symbol and interval
        self._candle_data: Dict[str, Dict[str, List[Candle]]] = {}

        # Current playback index for each symbol/interval
        self._playback_indices: Dict[str, Dict[str, int]] = {}

        # Playback state
        self._is_playing = False
        self._playback_tasks: List[asyncio.Task] = []

    async def initialize(self) -> None:
        """Initialize the backfill exchange."""
        try:
            # Initialize real exchange for fetching if needed
            self.real_exchange = await ExchangeFactory.create_exchange("BINANCE")
            self.logger.info("BackfillExchange initialized")
        except Exception as e:
            self.logger.error("Failed to initialize BackfillExchange: %s", e)
            raise

    def register_candle_callback(self, callback: Callable[[Candle], None]) -> None:
        """Register a callback for candle data."""
        if callback not in self.candle_callbacks:
            self.candle_callbacks.append(callback)
            self.logger.debug("Registered candle callback")

    async def get_candles(
        self, symbol: str, interval: Interval, start_date: datetime, end_date: datetime
    ) -> List[Candle]:
        """
        Get candles for a symbol and interval.

        First tries archive, then fetches from exchange if not found.
        """
        # Use archive manager's interval_to_frame for consistency
        interval_str = self.archive_manager.interval_to_frame(interval)

        # Check cache first
        if symbol in self._candle_data and interval_str in self._candle_data[symbol]:
            cached = self._candle_data[symbol][interval_str]
            # Filter by date range
            filtered = [
                c
                for c in cached
                if start_date.timestamp() * 1000 <= c.timestamp <= end_date.timestamp() * 1000
            ]
            if filtered:
                return filtered

        # Try archive
        archived = await self.archive_manager.get_candles(symbol, interval)
        if archived:
            # Filter by date range
            filtered = [
                c
                for c in archived
                if start_date.timestamp() * 1000 <= c.timestamp <= end_date.timestamp() * 1000
            ]
            if filtered:
                # Cache and return
                if symbol not in self._candle_data:
                    self._candle_data[symbol] = {}
                self._candle_data[symbol][interval_str] = filtered
                return filtered

        # Fetch from exchange if not in archive
        self.logger.info(
            "Data not in archive for %s %s, fetching from exchange...", symbol, interval_str
        )
        if not self.real_exchange:
            await self.initialize()

        candles = await self.real_exchange.fetch_historical_data(
            symbol, start_date, end_date, interval
        )

        # Archive the fetched data
        if candles:
            await self.archive_manager.archive_candles(symbol, candles, interval_str)

            # Cache
            if symbol not in self._candle_data:
                self._candle_data[symbol] = {}
            self._candle_data[symbol][interval_str] = candles

        return candles

    async def load_symbol_data(
        self, symbol: str, interval: Interval, start_date: datetime, end_date: datetime
    ) -> None:
        """
        Load all data for a symbol and interval into memory.

        This prepares data for playback.
        """
        interval_str = self.archive_manager.interval_to_frame(interval)

        candles = await self.get_candles(symbol, interval, start_date, end_date)

        if symbol not in self._candle_data:
            self._candle_data[symbol] = {}

        self._candle_data[symbol][interval_str] = candles

        # Initialize playback index
        if symbol not in self._playback_indices:
            self._playback_indices[symbol] = {}
        self._playback_indices[symbol][interval_str] = 0

        self.logger.info("Loaded %d candles for %s %s", len(candles), symbol, interval_str)

    async def start_playback(self, symbol: str, interval: Interval, speed: float = 1.0) -> None:
        """
        Start playing back historical candles.

        Args:
            symbol: Trading pair symbol
            interval: Candle interval
            speed: Playback speed multiplier (1.0 = real-time, 2.0 = 2x speed)
        """
        interval_str = self.archive_manager.interval_to_frame(interval)

        if symbol not in self._candle_data or interval_str not in self._candle_data[symbol]:
            raise ValueError(f"No data loaded for {symbol} {interval_str}")

        candles = self._candle_data[symbol][interval_str]
        if not candles:
            self.logger.warning("No candles to play back for %s %s", symbol, interval_str)
            return

        self._is_playing = True
        task = asyncio.create_task(self._playback_loop(symbol, interval_str, candles, speed))
        self._playback_tasks.append(task)
        self.logger.info("Started playback for %s %s", symbol, interval_str)

    async def _playback_loop(
        self, symbol: str, interval_str: str, candles: List[Candle], speed: float
    ) -> None:
        """Internal playback loop that emits candles."""
        index = self._playback_indices.get(symbol, {}).get(interval_str, 0)

        while index < len(candles) and self._is_playing:
            candle = candles[index]

            # Notify all callbacks
            for callback in self.candle_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(candle)
                    else:
                        callback(candle)
                except Exception as e:
                    self.logger.error("Error in candle callback: %s", e)

            index += 1
            self._playback_indices[symbol][interval_str] = index

            # Calculate delay based on interval and speed
            if index < len(candles):
                next_candle = candles[index]
                delay_ms = next_candle.timestamp - candle.timestamp
                delay_seconds = (delay_ms / 1000.0) / speed

                # Cap delay to prevent too long waits
                delay_seconds = min(delay_seconds, 1.0)
                await asyncio.sleep(delay_seconds)

        self.logger.info("Playback completed for %s %s", symbol, interval_str)

    def stop_playback(self) -> None:
        """Stop all playback tasks."""
        self._is_playing = False
        for task in self._playback_tasks:
            task.cancel()
        self._playback_tasks.clear()
        self.logger.info("Stopped all playback tasks")

    async def close(self) -> None:
        """Close and cleanup resources."""
        self.stop_playback()
        if self.real_exchange:
            await self.real_exchange.close()
        self.logger.info("BackfillExchange closed")

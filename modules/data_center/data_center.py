"""
Data Center for managing market data and technical indicators.

This is the central provider for all market data (candles and indicators)
used by the strategy manager. It supports both backfill (historical) and
production (real-time) modes.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from models.data_models.candle import Candle
from models.time_models import Interval, frame_to_interval
from modules.archive.archive_manager import ArchiveManager
from modules.config.config_manager import get_config
from modules.data.candle import Candle as DataCandle
from modules.exchange.backfill_exchange import BackfillExchange
from modules.exchange.exchange import Exchange
from modules.exchange.exchange_factory import ExchangeFactory
from modules.exchange.exchange_websocket import ExchangeWebSocket
from modules.indicator.indicator_manager import IndicatorManager
from modules.log import LogManager


class DataCenter:
    """
    Central data center for market data and indicators.

    Features:
    - Supports backfill mode (historical data replay)
    - Supports production mode (real-time WebSocket)
    - Automatically creates all available indicators
    - Provides normalized data access for strategies
    """

    def __init__(self, config_file: str = "config.ini"):
        """Initialize the data center."""
        self.config = get_config()
        self.logger = LogManager.get_logger()
        self.archive_manager = ArchiveManager(config_file)

        # Mode detection: backfill if development_mode is true
        self.is_backfill_mode = self.config.default.development_mode

        # Exchange instances
        self.exchange: Optional[Exchange] = None
        self.backfill_exchange: Optional[BackfillExchange] = None
        self.websocket: Optional[ExchangeWebSocket] = None

        # Data storage: {symbol: [Candle, ...]}
        self.candles: Dict[str, List[Candle]] = {}

        # Indicator manager
        self.indicator_manager: Optional[IndicatorManager] = None

        # Processing state
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        self.processing_tasks: List[asyncio.Task] = []

        # Symbol configuration
        self.symbols: List[str] = []
        self.interval: Interval = frame_to_interval(self.config.exchange.time_frame)

        # Indicator configurations - create all possible indicators
        self.indicator_configs = self._get_all_indicator_configs()

    def _get_all_indicator_configs(self) -> List[Dict]:
        """
        Get configurations for all available indicators.

        Creates multiple instances with different parameters for common indicators.
        """
        configs = []

        # SMA indicators with common periods
        for period in [9, 20, 50, 100, 200]:
            configs.append({"type": "SMA", "period": period})

        # EMA indicators with common periods
        for period in [9, 12, 26, 50, 100, 200]:
            configs.append({"type": "EMA", "period": period})

        # Parabolic SAR with common configurations
        configs.append({"type": "ParabolicSAR", "acceleration": 0.02, "maximum": 0.20})
        configs.append({"type": "ParabolicSAR", "acceleration": 0.02, "maximum": 0.20})

        return configs

    async def initialize(self) -> None:
        """Initialize the data center."""
        try:
            self.logger.info(
                "Initializing DataCenter in %s mode",
                "BACKFILL" if self.is_backfill_mode else "PRODUCTION",
            )

            # Initialize exchange based on mode
            if self.is_backfill_mode:
                await self._initialize_backfill_mode()
            else:
                await self._initialize_production_mode()

            # Initialize indicator manager with candle request callback
            self.indicator_manager = IndicatorManager(
                candle_request_callback=self._request_candle_callback
            )

            # Create indicators for all symbols
            await self._create_indicators_for_symbols()

            self.logger.info("DataCenter initialized successfully")

        except Exception as e:
            self.logger.error("Failed to initialize DataCenter: %s", e)
            raise

    async def _initialize_backfill_mode(self) -> None:
        """Initialize backfill mode with mock exchange."""
        self.logger.info("Initializing backfill mode...")
        self.backfill_exchange = BackfillExchange()
        await self.backfill_exchange.initialize()

        # Register callback for candles
        self.backfill_exchange.register_candle_callback(self._on_candle_received)

        # Initialize real exchange for fetching if needed
        exchange_code = self.config.exchange.exchange_code
        self.exchange = await ExchangeFactory.create_exchange(exchange_code)

        self.logger.info("Backfill mode initialized")

    async def _initialize_production_mode(self) -> None:
        """Initialize production mode with real exchange and WebSocket."""
        self.logger.info("Initializing production mode...")

        exchange_code = self.config.exchange.exchange_code
        self.exchange = await ExchangeFactory.create_exchange(exchange_code)

        # Create and initialize WebSocket
        self.websocket = ExchangeFactory.create_websocket(exchange_code)
        self.websocket.register_candle_callback(self._on_candle_received)

        # Set logger for websocket
        self.websocket.set_logger(self.logger)

        self.logger.info("Production mode initialized")

    def _request_candle_callback(
        self, symbol: str, index: int = 0, reverse: bool = False
    ) -> Optional[Candle]:
        """
        Callback for IndicatorManager to request candles.

        This provides normalized access to historical candles.
        """
        if symbol not in self.candles:
            return None

        candles = self.candles[symbol]
        if not candles:
            return None

        if reverse:
            # Index from end (most recent first)
            idx = len(candles) - 1 - index
        else:
            # Index from start (oldest first)
            idx = index

        if idx < 0 or idx >= len(candles):
            return None

        return candles[idx]

    async def _create_indicators_for_symbols(self) -> None:
        """Create all configured indicators for each symbol."""
        if not self.indicator_manager:
            return

        for symbol in self.symbols:
            for config in self.indicator_configs:
                try:
                    # Create a copy to avoid modifying the original
                    config_copy = config.copy()
                    indicator_type = config_copy.pop("type")
                    indicator = self.indicator_manager.create_indicator(
                        indicator_type, symbol, **config_copy
                    )
                    self.logger.debug(
                        "Created indicator %s for symbol %s", indicator.code, symbol
                    )
                except Exception as e:
                    self.logger.error(
                        "Failed to create indicator %s for %s: %s",
                        config.get("type", "unknown"),
                        symbol,
                        e,
                    )

    def add_symbol(self, symbol: str) -> None:
        """Add a symbol to track."""
        if symbol not in self.symbols:
            self.symbols.append(symbol)
            self.candles[symbol] = []
            self.logger.info("Added symbol %s", symbol)

    async def start(self) -> None:
        """Start the data center."""
        if self.is_running:
            self.logger.warning("DataCenter is already running")
            return

        try:
            self.logger.info("Starting DataCenter...")
            self.is_running = True

            if self.is_backfill_mode:
                await self._start_backfill_mode()
            else:
                await self._start_production_mode()

            # Start processing task
            self.processing_tasks.append(asyncio.create_task(self._processing_loop()))

            self.logger.info("DataCenter started successfully")

        except Exception as e:
            self.logger.error("Failed to start DataCenter: %s", e)
            raise

    async def _start_backfill_mode(self) -> None:
        """Start backfill mode."""
        if not self.backfill_exchange:
            await self._initialize_backfill_mode()

        # Load data for all symbols
        # Determine date range from config or use defaults
        end_date = datetime.utcnow()
        start_date = datetime(2020, 1, 1)  # Default start date

        for symbol in self.symbols:
            await self.backfill_exchange.load_symbol_data(
                symbol, self.interval, start_date, end_date
            )

            # Start playback
            await self.backfill_exchange.start_playback(
                symbol, self.interval, speed=100.0
            )

    async def _start_production_mode(self) -> None:
        """Start production mode with WebSocket."""
        if not self.websocket:
            await self._initialize_production_mode()

        # Connect WebSocket
        await self.websocket.connect()

        # Subscribe to symbols
        if self.symbols:
            await self.websocket.subscribe(self.symbols, self.interval)

    async def _processing_loop(self) -> None:
        """Main processing loop for handling shutdown."""
        try:
            await self.shutdown_event.wait()
        except Exception as e:
            self.logger.error("Error in processing loop: %s", e)

    async def _on_candle_received(self, candle: Candle) -> None:
        """
        Handle new candle from exchange (backfill or production).

        This normalizes the candle and calculates all indicators.
        """
        try:
            # Normalize candle (ensure it's using the standard Candle model)
            normalized_candle = self._normalize_candle(candle)

            # Store candle
            symbol = normalized_candle.symbol
            if symbol not in self.candles:
                self.candles[symbol] = []

            self.candles[symbol].append(normalized_candle)

            # Calculate all indicators for this candle
            await self._calculate_indicators(normalized_candle)

            self.logger.debug("Processed candle for %s: %s", symbol, normalized_candle)

        except Exception as e:
            self.logger.error("Error processing candle: %s", e)

    def _normalize_candle(self, candle) -> Candle:
        """
        Normalize candle to standard format.

        This ensures all candles follow the same structure regardless of source.
        """
        # If already a Candle from models.data_models, return as-is
        ModelCandle = Candle  # Use the imported Candle class

        if isinstance(candle, ModelCandle):
            return candle

        # Convert from modules.data.candle.Candle if needed
        if isinstance(candle, DataCandle):
            return ModelCandle(
                symbol=candle.symbol,
                timestamp=candle.timestamp,
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
                trade_count=getattr(candle, "trade_count", None),
            )

        # If it's a dict or has attributes, try to construct
        if hasattr(candle, "symbol") and hasattr(candle, "timestamp"):
            return ModelCandle(
                symbol=candle.symbol,
                timestamp=candle.timestamp,
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
                trade_count=getattr(candle, "trade_count", None),
            )

        # Default: assume it's already correct
        return candle

    async def _calculate_indicators(self, candle: Candle) -> None:
        """Calculate all indicators for a given candle."""
        if not self.indicator_manager:
            return

        symbol = candle.symbol

        # Get all indicators for this symbol
        indicators = self.indicator_manager.get_all_indicators_for_symbol(symbol)

        # Calculate each indicator
        for indicator_code, indicator in indicators.items():
            try:
                value = indicator.calculate(candle)
                if value is not None:
                    self.logger.debug(
                        "Calculated %s for %s: %.8f", indicator_code, symbol, value
                    )
            except Exception as e:
                self.logger.error(
                    "Error calculating indicator %s for %s: %s",
                    indicator_code,
                    symbol,
                    e,
                )

    async def backfill(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: Optional[Interval] = None,
    ) -> List[Candle]:
        """
        Backfill historical data for a symbol.

        Uses exchange method to fetch data if needed.
        """
        if not self.exchange:
            await self._initialize_backfill_mode()

        interval_to_use = interval or self.interval

        self.logger.info(
            "Backfilling %s from %s to %s (interval: %s)",
            symbol,
            start_date,
            end_date,
            interval_to_use,
        )

        candles = await self.exchange.fetch_historical_data(
            symbol, start_date, end_date, interval_to_use
        )

        # Archive the data
        if candles:
            await self.archive_manager.archive_candles(
                symbol, candles, self.archive_manager.interval_to_frame(interval_to_use)
            )

            # Add to storage
            if symbol not in self.candles:
                self.candles[symbol] = []
            self.candles[symbol].extend(candles)

            # Calculate indicators for all new candles
            for candle in candles:
                await self._calculate_indicators(candle)

        self.logger.info("Backfilled %d candles for %s", len(candles), symbol)
        return candles

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

    def get_indicator_value(
        self,
        symbol: str,
        indicator_code: str,
        index: int = 0,
        reverse: bool = False,
    ) -> Optional[float]:
        """
        Get an indicator value.

        Args:
            symbol: Trading pair symbol
            indicator_code: Indicator code (e.g., "sma_20", "ema_9")
            index: Index offset
            reverse: If True, index from most recent

        Returns:
            Indicator value or None
        """
        if not self.indicator_manager:
            return None

        return self.indicator_manager.get_indicator_value(
            symbol, indicator_code, index, reverse
        )

    def get_all_indicators(self, symbol: str) -> Dict[str, object]:
        """
        Get all indicators for a symbol.

        Returns:
            Dictionary of indicator_code -> indicator_instance
        """
        if not self.indicator_manager:
            return {}

        return self.indicator_manager.get_all_indicators_for_symbol(symbol)

    async def stop(self) -> None:
        """Stop the data center."""
        if not self.is_running:
            return

        self.logger.info("Stopping DataCenter...")
        self.is_running = False
        self.shutdown_event.set()

        # Cancel processing tasks
        for task in self.processing_tasks:
            task.cancel()

        await asyncio.gather(*self.processing_tasks, return_exceptions=True)
        self.processing_tasks.clear()

        # Stop backfill playback
        if self.backfill_exchange:
            self.backfill_exchange.stop_playback()
            await self.backfill_exchange.close()

        # Disconnect WebSocket
        if self.websocket:
            await self.websocket.unsubscribe(self.symbols, self.interval)
            await self.websocket.disconnect()
            await self.websocket.cleanup()

        # Close exchange
        if self.exchange:
            await self.exchange.close()

        self.logger.info("DataCenter stopped")

    async def shutdown(self) -> None:
        """Shutdown the data center."""
        await self.stop()

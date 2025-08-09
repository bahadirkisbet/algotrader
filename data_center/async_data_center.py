import asyncio
import datetime
import logging
from typing import Any, Dict, List, Optional

from data_provider.exchange_collection.exchange import Exchange

from managers.async_archive_manager import AsyncArchiveManager
from managers.technical_indicators import (
    ExponentialMovingAverage,
    SimpleMovingAverage,
    TechnicalIndicator,
)
from models.data_models.candle import Candle
from models.time_models import Interval


class AsyncDataCenter:
    """Asynchronous data center for managing market data and technical indicators."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.symbols: Dict[str, List[Candle]] = {}
        self.exchange: Optional[Exchange] = None
        self.archiver: Optional[AsyncArchiveManager] = None
        
        # Async components
        self.__running__ = False
        self.__shutdown_event__ = asyncio.Event()
        self.__tasks__: List[asyncio.Task] = []
        self.__buffer__ = asyncio.Queue()
        
        # Technical indicators
        self.indicator_codes: List[str] = []
        
        # Initialize
        self.__initialize__()
    
    def __initialize__(self):
        """Initialize the data center."""
        try:
            # Fetch product list
            asyncio.create_task(self.fetch_product_list())
            
            # Initialize indicators
            self.__initialize_indicators__()
            
            self.logger.info("AsyncDataCenter initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AsyncDataCenter: {e}")
            raise
    
    def __initialize_indicators__(self):
        """Initialize technical indicators."""
        try:
            # Add default indicators
            self.indicator_codes = [
                "SMA_20",
                "EMA_12",
                "EMA_26"
            ]
            
            self.logger.info(f"Initialized {len(self.indicator_codes)} indicators")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize indicators: {e}")
    
    async def start(self):
        """Start the data center."""
        if self.__running__:
            self.logger.warning("Data center is already running")
            return
        
        try:
            self.logger.info("Starting AsyncDataCenter...")
            self.__running__ = True
            
            # Start data processing task
            self.__tasks__.append(
                asyncio.create_task(self.__process_data__())
            )
            
            # Start indicator calculation task
            self.__tasks__.append(
                asyncio.create_task(self.__start_calculating_indicators__())
            )
            
            self.logger.info("AsyncDataCenter started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start AsyncDataCenter: {e}")
            raise
    
    async def stop(self):
        """Stop the data center."""
        if not self.__running__:
            return
        
        self.logger.info("Stopping AsyncDataCenter...")
        self.__running__ = False
        self.__shutdown_event__.set()
        
        # Cancel all tasks
        for task in self.__tasks__:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.__tasks__:
            await asyncio.gather(*self.__tasks__, return_exceptions=True)
        
        self.logger.info("AsyncDataCenter stopped")
    
    async def shutdown(self):
        """Shutdown the data center."""
        await self.stop()
    
    async def fetch_product_list(self) -> List[str]:
        """Fetch product list from exchange."""
        try:
            if not self.exchange:
                self.logger.warning("No exchange configured")
                return []
            
            products = await self.exchange.fetch_product_list()
            self.logger.info(f"Fetched {len(products)} products")
            return products
            
        except Exception as e:
            self.logger.error(f"Failed to fetch product list: {e}")
            return []
    
    async def fetch_historical_data(self, symbol: str, interval: Interval, 
                                   start_date: datetime.datetime, 
                                   end_date: datetime.datetime) -> List[Candle]:
        """Fetch historical data for a symbol."""
        try:
            if not self.exchange:
                self.logger.warning("No exchange configured")
                return []
            
            candles = await self.exchange.fetch_ohlcv(symbol, start_date, end_date, interval)
            
            # Store in memory
            if symbol not in self.symbols:
                self.symbols[symbol] = []
            
            # Check for duplicates and gaps
            candles = self.__check_duplicate__(candles)
            await self.__fill_gaps__(symbol, candles, start_date, end_date, interval)
            
            # Store candles
            self.symbols[symbol].extend(candles)
            
            # Archive data
            if self.archiver:
                await self.archiver.save(
                    exchange_code="BINANCE",  # Default, should be configurable
                    symbol=symbol,
                    data_type="CANDLE",
                    data_frame=interval.value,
                    data=candles
                )
            
            self.logger.info(f"Fetched {len(candles)} historical candles for {symbol}")
            return candles
            
        except Exception as e:
            self.logger.error(f"Failed to fetch historical data for {symbol}: {e}")
            return []
    
    async def __fill_gaps__(self, symbol: str, candles: List[Candle], 
                           start_date: datetime.datetime, end_date: datetime.datetime, 
                           interval: Interval):
        """Fill gaps in historical data."""
        try:
            if not candles:
                return
            
            # Sort candles by timestamp
            candles.sort(key=lambda x: x.timestamp)
            
            # Check for gaps
            expected_timestamps = []
            current = start_date
            
            while current <= end_date:
                expected_timestamps.append(current)
                current += datetime.timedelta(minutes=interval.value)
            
            # Find missing timestamps
            actual_timestamps = {c.timestamp for c in candles}
            missing_timestamps = [ts for ts in expected_timestamps if ts not in actual_timestamps]
            
            if missing_timestamps:
                self.logger.info(f"Found {len(missing_timestamps)} gaps in {symbol} data")
                
                # Create gap candles (placeholder with previous close or 0)
                gap_candles = []
                for ts in missing_timestamps:
                    # Find previous candle for close price
                    prev_close = 0.0
                    for candle in reversed(candles):
                        if candle.timestamp < ts:
                            prev_close = candle.close
                            break
                    
                    gap_candle = Candle(
                        symbol=symbol,
                        timestamp=int(ts.timestamp() * 1000),  # Convert to milliseconds
                        open=prev_close,
                        high=prev_close,
                        low=prev_close,
                        close=prev_close,
                        volume=0.0,
                        trade_count=0
                    )
                    gap_candles.append(gap_candle)
                
                # Insert gap candles
                self.__insert_gap_candles__(symbol, gap_candles, start_date)
                
        except Exception as e:
            self.logger.error(f"Error filling gaps for {symbol}: {e}")
    
    def __insert_gap_candles__(self, symbol: str, gap_candles: List[Candle], gap_start: datetime.datetime):
        """Insert gap candles in the correct position."""
        try:
            symbol_data = self.symbols[symbol]
            
            # Find insertion index
            insert_index = 0
            for i, candle in enumerate(symbol_data):
                if candle.timestamp > gap_start:
                    insert_index = i
                    break
                insert_index = i + 1
            
            # Insert gap candles
            for candle in gap_candles:
                symbol_data.insert(insert_index, candle)
                insert_index += 1
                
        except Exception as e:
            self.logger.error(f"Error inserting gap candles: {e}")
    
    def __check_duplicate__(self, archived_data):
        """Check for duplicate candles in archived data."""
        try:
            seen_timestamps = set()
            unique_data = []
            
            for candle in archived_data:
                if candle.timestamp not in seen_timestamps:
                    seen_timestamps.add(candle.timestamp)
                    unique_data.append(candle)
                else:
                    self.logger.warning(f"Duplicate candle found: {candle.timestamp}")
            
            return unique_data
            
        except Exception as e:
            self.logger.error(f"Error checking duplicates: {e}")
            return archived_data
    
    async def request_candle(self, symbol: str, index: int = 0, reverse: bool = False) -> Optional[Candle]:
        """Request a specific candle by index."""
        try:
            if symbol not in self.symbols:
                return None
            
            symbol_data = self.symbols[symbol]
            if not symbol_data:
                return None
            
            if reverse:
                index = len(symbol_data) - 1 - index
            
            if 0 <= index < len(symbol_data):
                return symbol_data[index]
            else:
                self.logger.warning(f"Index {index} out of range for symbol {symbol}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error requesting candle: {e}")
            return None
    
    async def __start_calculating_indicators__(self):
        """Start calculating technical indicators."""
        try:
            for indicator_code in self.indicator_codes:
                indicator = self.__create_indicator__(indicator_code)
                if indicator:
                    for symbol in self.symbols.keys():
                        await self.__start_calculating_indicator__(indicator, symbol)
                        
        except Exception as e:
            self.logger.error(f"Failed to start calculating indicators: {e}")
    
    def __create_indicator__(self, indicator_code: str) -> Optional[TechnicalIndicator]:
        """Create a technical indicator instance."""
        try:
            if indicator_code == "SMA_20":
                return SimpleMovingAverage(20)
            elif indicator_code == "EMA_12":
                return ExponentialMovingAverage(12)
            elif indicator_code == "EMA_26":
                return ExponentialMovingAverage(26)
            else:
                self.logger.warning(f"Unknown indicator code: {indicator_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create indicator {indicator_code}: {e}")
            return None
    
    async def __start_calculating_indicator__(self, indicator: TechnicalIndicator, symbol: str) -> None:
        """Start calculating a specific indicator for a symbol."""
        try:
            if symbol in self.symbols and self.symbols[symbol]:
                # Calculate indicator for existing data
                result = indicator.calculate(self.symbols[symbol])
                self.logger.debug(f"Calculated {indicator.__class__.__name__} for {symbol}")
                
        except Exception as e:
            self.logger.error(f"Failed to calculate indicator for {symbol}: {e}")
    
    async def __calculate_candle__(self, candle: Candle):
        """Calculate indicators for a new candle."""
        try:
            for indicator_code in self.indicator_codes:
                indicator = self.__create_indicator__(indicator_code)
                if indicator and candle.symbol in self.symbols:
                    # Calculate indicator with new candle
                    symbol_data = self.symbols[candle.symbol]
                    result = indicator.calculate(symbol_data)
                    
        except Exception as e:
            self.logger.error(f"Error calculating indicators for candle: {e}")
    
    async def __process_data__(self):
        """Process incoming data from the buffer."""
        try:
            while not self.__shutdown_event__.is_set():
                try:
                    # Process data from buffer
                    data = await asyncio.wait_for(self.__buffer__.get(), timeout=1.0)
                    
                    if isinstance(data, Candle):
                        await self.__process_candle__(data)
                    elif isinstance(data, dict):
                        await self.__process_message__(data)
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    self.logger.error(f"Error processing data: {e}")
                    await asyncio.sleep(1)
                    
        except Exception as e:
            self.logger.error(f"Fatal error in data processing: {e}")
    
    async def __process_candle__(self, candle: Candle):
        """Process a single candle."""
        try:
            symbol = candle.symbol
            
            # Store candle
            if symbol not in self.symbols:
                self.symbols[symbol] = []
            
            self.symbols[symbol].append(candle)
            
            # Calculate indicators
            await self.__calculate_candle__(candle)
            
            # Archive if needed
            if self.archiver:
                await self.archiver.archive_candle(candle)
            
            self.logger.debug(f"Processed candle for {symbol}: {candle.timestamp}")
            
        except Exception as e:
            self.logger.error(f"Error processing candle: {e}")
    
    async def __process_message__(self, message: Dict[str, Any]):
        """Process a message from the exchange."""
        try:
            # Handle different message types
            if message.get("type") == "candle":
                candle_data = message.get("data", {})
                candle = Candle(
                    symbol=candle_data.get("symbol"),
                    timestamp=candle_data.get("timestamp"),
                    open=candle_data.get("open"),
                    high=candle_data.get("high"),
                    low=candle_data.get("low"),
                    close=candle_data.get("close"),
                    volume=candle_data.get("volume"),
                    trade_count=candle_data.get("trade_count", 0)
                )
                await self.__process_candle__(candle)
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
    
    def add_candle(self, candle: Candle):
        """Add a candle to the processing buffer."""
        try:
            self.__buffer__.put_nowait(candle)
        except asyncio.QueueFull:
            self.logger.warning("Data buffer is full, dropping candle")
    
    def add_message(self, message: Dict[str, Any]):
        """Add a message to the processing buffer."""
        try:
            self.__buffer__.put_nowait(message)
        except asyncio.QueueFull:
            self.logger.warning("Data buffer is full, dropping message")
    
    def set_exchange(self, exchange: Exchange):
        """Set the exchange instance."""
        self.exchange = exchange
    
    def set_archiver(self, archiver: AsyncArchiveManager):
        """Set the archive manager instance."""
        self.archiver = archiver
    
    def is_running(self) -> bool:
        """Check if the data center is running."""
        return self.__running__
    
    def get_symbol_count(self) -> int:
        """Get the number of symbols being tracked."""
        return len(self.symbols)
    
    def get_candle_count(self, symbol: str) -> int:
        """Get the number of candles for a specific symbol."""
        return len(self.symbols.get(symbol, []))
    
    async def get_status(self) -> Dict[str, Any]:
        """Get the current status of the data center."""
        return {
            "running": self.__running__,
            "symbol_count": self.get_symbol_count(),
            "buffer_size": self.__buffer__.qsize(),
            "shutdown_requested": self.__shutdown_event__.is_set(),
            "active_tasks": len([t for t in self.__tasks__ if not t.done()])
        } 
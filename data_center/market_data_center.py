import asyncio
import datetime
import logging
from typing import Any, Dict, List, Optional

from data_provider.exchange_collection.exchange import Exchange

from modules.archive import ArchiveManager
from modules.strategy import (
    ExponentialMovingAverage,
    SimpleMovingAverage,
    TechnicalIndicator,
)
from models.data_models.candle import Candle
from models.time_models import Interval


class MarketDataCenter:
    """Market data center for managing market data and technical indicators."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.symbols: Dict[str, List[Candle]] = {}
        self.exchange: Optional[Exchange] = None
        self.archiver: Optional[ArchiveManager] = None
        
        # Async components
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        self.tasks: List[asyncio.Task] = []
        self.data_buffer = asyncio.Queue()
        
        # Technical indicators
        self.indicator_codes: List[str] = []
        
        # Initialize
        self.initialize()
    
    def initialize(self):
        """Initialize the data center."""
        try:
            # Fetch product list
            asyncio.create_task(self.fetch_product_list())
            
            # Initialize indicators
            self.initialize_indicators()
            
            self.logger.info("MarketDataCenter initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MarketDataCenter: {e}")
            raise
    
    def initialize_indicators(self):
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
        if self.is_running:
            self.logger.warning("Data center is already running")
            return
        
        try:
            self.logger.info("Starting MarketDataCenter...")
            self.is_running = True
            
            # Start data processing task
            self.tasks.append(
                asyncio.create_task(self.process_data())
            )
            
            # Start indicator calculation task
            self.tasks.append(
                asyncio.create_task(self.start_calculating_indicators())
            )
            
            self.logger.info("MarketDataCenter started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start MarketDataCenter: {e}")
            raise
    
    async def stop(self):
        """Stop the data center."""
        if not self.is_running:
            return
        
        self.logger.info("Stopping MarketDataCenter...")
        self.is_running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        
        self.logger.info("MarketDataCenter stopped successfully")
    
    async def shutdown(self):
        """Shutdown the data center."""
        await self.stop()
        self.shutdown_event.set()
    
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
                self.logger.error("No exchange set")
                return []
            
            # Fetch data from exchange
            candles = await self.exchange.fetch_historical_data(
                symbol, start_date, end_date, interval
            )
            
            # Remove duplicates and fill gaps
            candles = self.check_duplicate_candles(candles)
            await self.fill_data_gaps(symbol, candles, start_date, end_date, interval)
            
            # Store in memory
            if symbol not in self.symbols:
                self.symbols[symbol] = []
            
            self.symbols[symbol].extend(candles)
            
            # Archive data
            if self.archiver:
                await self.archiver.archive_candles(symbol, candles)
            
            self.logger.info(f"Fetched {len(candles)} candles for {symbol}")
            return candles
            
        except Exception as e:
            self.logger.error(f"Failed to fetch historical data for {symbol}: {e}")
            return []

    async def fill_data_gaps(self, symbol: str, candles: List[Candle], 
                           start_date: datetime.datetime, end_date: datetime.datetime, 
                           interval: Interval):
        """Fill gaps in historical data."""
        try:
            if not candles:
                return
            
            # Sort candles by timestamp
            candles.sort(key=lambda x: x.timestamp)
            
            # Find gaps
            gap_start = None
            gap_end = None
            
            for i in range(len(candles) - 1):
                current_time = candles[i].timestamp
                next_time = candles[i + 1].timestamp
                
                # Calculate expected next time based on interval
                expected_next = current_time + interval.to_seconds()
                
                if next_time > expected_next:
                    gap_start = current_time
                    gap_end = next_time
                    break
            
            if gap_start and gap_end:
                self.logger.info(f"Filling gap in {symbol} from {gap_start} to {gap_end}")
                
                # Fetch missing data
                gap_candles = await self.exchange.fetch_historical_data(
                    symbol, gap_start, gap_end, interval
                )
                
                # Insert gap candles
                self.insert_gap_candles(symbol, gap_candles, gap_start)
                
        except Exception as e:
            self.logger.error(f"Error filling gaps for {symbol}: {e}")

    def insert_gap_candles(self, symbol: str, gap_candles: List[Candle], gap_start: datetime.datetime):
        """Insert gap candles into the symbol's data."""
        try:
            if symbol not in self.symbols:
                self.symbols[symbol] = []
            
            # Find insertion point
            insert_index = 0
            for i, candle in enumerate(self.symbols[symbol]):
                if candle.timestamp >= gap_start:
                    insert_index = i
                    break
            
            # Insert gap candles
            self.symbols[symbol][insert_index:insert_index] = gap_candles
            
            self.logger.info(f"Inserted {len(gap_candles)} gap candles for {symbol}")
            
        except Exception as e:
            self.logger.error(f"Error inserting gap candles for {symbol}: {e}")

    def check_duplicate_candles(self, archived_data):
        """Check and remove duplicate candles."""
        try:
            if not archived_data:
                return archived_data
            
            # Remove duplicates based on timestamp
            seen_timestamps = set()
            unique_candles = []
            
            for candle in archived_data:
                if candle.timestamp not in seen_timestamps:
                    seen_timestamps.add(candle.timestamp)
                    unique_candles.append(candle)
            
            removed_count = len(archived_data) - len(unique_candles)
            if removed_count > 0:
                self.logger.info(f"Removed {removed_count} duplicate candles")
            
            return unique_candles
            
        except Exception as e:
            self.logger.error(f"Error checking duplicates: {e}")
            return archived_data

    async def request_candle(self, symbol: str, index: int = 0, reverse: bool = False) -> Optional[Candle]:
        """Request a specific candle by index."""
        try:
            if symbol not in self.symbols:
                self.logger.warning(f"Symbol {symbol} not found in data center")
                return None
            
            candles = self.symbols[symbol]
            if not candles:
                return None
            
            if reverse:
                # Get from end (most recent)
                if index >= len(candles):
                    return None
                return candles[-(index + 1)]
            else:
                # Get from beginning (oldest)
                if index >= len(candles):
                    return None
                return candles[index]
                
        except Exception as e:
            self.logger.error(f"Error requesting candle for {symbol}: {e}")
            return None

    async def start_calculating_indicators(self):
        """Start calculating technical indicators."""
        try:
            for symbol in self.symbols:
                for indicator_code in self.indicator_codes:
                    indicator = self.create_indicator(indicator_code)
                    if indicator:
                        await self.start_calculating_indicator(indicator, symbol)
                        
        except Exception as e:
            self.logger.error(f"Error calculating indicators for candle: {e}")

    def create_indicator(self, indicator_code: str) -> Optional[TechnicalIndicator]:
        """Create a technical indicator instance based on code."""
        try:
            if indicator_code.startswith("SMA_"):
                period = int(indicator_code.split("_")[1])
                return SimpleMovingAverage(period)
            elif indicator_code.startswith("EMA_"):
                period = int(indicator_code.split("_")[1])
                return ExponentialMovingAverage(period)
            else:
                self.logger.warning(f"Unknown indicator code: {indicator_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating indicator {indicator_code}: {e}")
            return None

    async def start_calculating_indicator(self, indicator: TechnicalIndicator, symbol: str) -> None:
        """Start calculating a specific indicator for a symbol."""
        try:
            # Calculate indicator for existing candles
            if symbol in self.symbols:
                candles = self.symbols[symbol]
                value = indicator.calculate(candles)
                if value is not None:
                    self.logger.debug(f"Calculated {indicator.__class__.__name__} for {symbol}")
                    
        except Exception as e:
            self.logger.error(f"Error calculating indicator for {symbol}: {e}")

    async def calculate_candle(self, candle: Candle):
        """Calculate indicators for a specific candle."""
        try:
            for indicator_code in self.indicator_codes:
                indicator = self.create_indicator(indicator_code)
                if indicator:
                    # Calculate with recent candles
                    symbol_candles = self.symbols.get(candle.symbol, [])
                    value = indicator.calculate(symbol_candles)
                    
        except Exception as e:
            self.logger.error(f"Error calculating indicators for candle: {e}")

    async def process_data(self):
        """Process incoming data from the buffer."""
        try:
            while not self.shutdown_event.is_set():
                try:
                    # Process data from buffer
                    data = await asyncio.wait_for(self.data_buffer.get(), timeout=1.0)
                    
                    if isinstance(data, Candle):
                        await self.process_candle(data)
                    elif isinstance(data, dict):
                        await self.process_message(data)
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    self.logger.error(f"Error processing data: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error in data processing loop: {e}")

    async def process_candle(self, candle: Candle):
        """Process a single candle."""
        try:
            # Add to symbol data
            if candle.symbol not in self.symbols:
                self.symbols[candle.symbol] = []
            
            self.symbols[candle.symbol].append(candle)
            
            # Calculate indicators
            await self.calculate_candle(candle)
            
            # Archive if needed
            if self.archiver:
                await self.archiver.archive_candles(candle.symbol, [candle])
                
        except Exception as e:
            self.logger.error(f"Error processing candle: {e}")

    async def process_message(self, message: Dict[str, Any]):
        """Process a message from websocket or other sources."""
        try:
            # Handle different message types
            if "candle" in message:
                candle_data = message["candle"]
                candle = Candle(
                    symbol=candle_data["symbol"],
                    timestamp=candle_data["timestamp"],
                    open_price=candle_data["open"],
                    high_price=candle_data["high"],
                    low_price=candle_data["low"],
                    close_price=candle_data["close"],
                    volume=candle_data["volume"],
                    interval=candle_data.get("interval", 1)
                )
                await self.process_candle(candle)
                
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    def add_candle(self, candle: Candle):
        """Add a candle to the processing buffer."""
        try:
            self.data_buffer.put_nowait(candle)
        except asyncio.QueueFull:
            self.logger.warning("Data buffer is full, dropping candle")

    def add_message(self, message: Dict[str, Any]):
        """Add a message to the processing buffer."""
        try:
            self.data_buffer.put_nowait(message)
        except asyncio.QueueFull:
            self.logger.warning("Data buffer is full, dropping message")

    def set_exchange(self, exchange: Exchange):
        """Set the exchange instance."""
        self.exchange = exchange

    def set_archiver(self, archiver: ArchiveManager):
        """Set the archive manager instance."""
        self.archiver = archiver

    def is_running(self) -> bool:
        """Check if the data center is running."""
        return self.is_running

    def get_symbol_count(self) -> int:
        """Get the number of symbols being tracked."""
        return len(self.symbols)

    def get_candle_count(self, symbol: str) -> int:
        """Get the number of candles for a symbol."""
        return len(self.symbols.get(symbol, []))

    async def get_status(self) -> Dict[str, Any]:
        """Get the current status of the data center."""
        return {
            "running": self.is_running,
            "symbol_count": self.get_symbol_count(),
            "buffer_size": self.data_buffer.qsize(),
            "shutdown_requested": self.shutdown_event.is_set(),
            "active_tasks": len([t for t in self.tasks if not t.done()])
        } 
import configparser
import datetime
import logging
import signal
from queue import Queue
from threading import Event, Thread
from typing import Dict, List, Optional

from algotrader.modules.archive.archive_manager import ArchiveManager
from data_provider.exchange_collection.exchange import Exchange

from data_center.jobs.technical_indicator import TechnicalIndicator
from data_center.jobs.technical_indicators.ema import ExponentialMovingAverage
from data_center.jobs.technical_indicators.sma import SimpleMovingAverage
from managers.websocket_manager import WebsocketManager
from models.data_models.candle import Candle
from models.time_models import Interval
from utils.singleton_metaclass.singleton import Singleton


class DataCenter(metaclass=Singleton):
    """Central data management system for algorithmic trading."""
    
    def __init__(self):
        self.exchange: Exchange = ServiceManager.get_service("exchange")
        self.logger: logging.Logger = ServiceManager.get_service("logger")
        self.config: configparser.ConfigParser = ServiceManager.get_service("config")
        self.archiver: ArchiveManager = ServiceManager.get_service("archiver")

        self.__run_forever__: bool = True
        self.__backfill__: bool = True
        self.__thread__: Optional[Thread] = None
        self.__shutdown_event__ = Event()
        self.data_type = "CANDLE"
        
        # Get time frame from config instead of hardcoding
        time_frame_str = self.config.get("EXCHANGE", "default_interval", fallback="1m")
        self.__time_frame__: Interval = self.__parse_interval__(time_frame_str)

        self.symbols: Dict[str, List[Candle]] = {}
        self.__buffer__: Queue[Optional[Candle]] = Queue()
        self.indicator_codes = []

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.__signal_handler__)
        signal.signal(signal.SIGTERM, self.__signal_handler__)

        # register callbacks
        self.exchange.register_candle_callback(self.push_candle)

        # initialize
        self.__initialize__()

    def __parse_interval__(self, interval_str: str) -> Interval:
        """Parse interval string to Interval enum."""
        try:
            # Map common interval strings to Interval enum values
            interval_map = {
                "1m": Interval.ONE_MINUTE,
                "5m": Interval.FIVE_MINUTES,
                "15m": Interval.FIFTEEN_MINUTES,
                "1h": Interval.ONE_HOUR,
                "4h": Interval.FOUR_HOURS,
                "1d": Interval.ONE_DAY
            }
            return interval_map.get(interval_str, Interval.ONE_MINUTE)
        except Exception as e:
            self.logger.warning(f"Failed to parse interval '{interval_str}', using default: {e}")
            return Interval.ONE_MINUTE

    def __signal_handler__(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.close()

    def start(self):
        """Start the data center with proper error handling."""
        try:
            # start the thread for listening to the events
            self.__thread__ = Thread(target=self.run_forever, args=(), daemon=True)
            self.__thread__.start()

            # subscribe to the websocket
            self.exchange.subscribe_to_websocket(list(self.symbols.keys()), self.__time_frame__)
            
            self.logger.info("DataCenter started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start DataCenter: {e}")
            raise

    def fetch_product_list(self):
        """Fetch product list with error handling and logging."""
        try:
            # TODO: sorting option and limit will be added later from config file
            symbols = self.exchange.fetch_product_list()
            self.logger.info(f"Total symbols: {len(symbols)} in the exchange {self.exchange.get_exchange_name()}")
            return symbols
        except Exception as e:
            self.logger.error(f"Failed to fetch product list: {e}")
            raise

    def push_candle(self, candle: Optional[Candle]):
        """Push candle to the processing queue."""
        try:
            if candle is not None:
                self.__buffer__.put(candle)
        except Exception as e:
            self.logger.error(f"Failed to push candle: {e}")

    def print_info(self, message: str, error_code: str):
        """Log information with proper formatting."""
        self.logger.info(f"{message} {error_code}")

    def backfill(self,
                 symbol: str,
                 start_date: datetime.datetime,
                 end_date: datetime.datetime,
                 interval: Interval) -> List[Candle]:
        """Backfill historical data with error handling."""
        try:
            self.logger.info(f"Back-filling {symbol} from {start_date} to {end_date} with interval {interval}...")
            candles = self.exchange.fetch_candle(symbol, start_date, end_date, interval)
            self.logger.info(f"Back-filling {symbol} from {start_date} to {end_date} with interval {interval}...Done")
            return candles
        except Exception as e:
            self.logger.error(f"Failed to backfill {symbol}: {e}")
            return []

    def run_forever(self):
        """Main processing loop with proper error handling."""
        self.logger.info("DataCenter processing loop started")
        
        while self.__run_forever__ and not self.__shutdown_event__.is_set():
            try:
                candle = self.__buffer__.get(timeout=1.0)  # Add timeout to allow graceful shutdown
                if candle is not None:
                    if candle.symbol in self.symbols:
                        self.symbols[candle.symbol].append(candle)
                        self.logger.debug(f"Processed candle: {candle}")
                        self.__calculate_candle__(candle)
                    else:
                        self.logger.warning(f"Received candle for unknown symbol: {candle.symbol}")
                        
            except Exception as e:
                if not self.__shutdown_event__.is_set():
                    self.logger.error(f"Error in processing loop: {e}")
                    continue
                else:
                    break
                    
        self.logger.info("DataCenter exited from the processing loop")

    def close(self):
        """Close the data center gracefully."""
        try:
            self.logger.info("Shutting down DataCenter...")
            
            # Signal shutdown
            self.__run_forever__ = False
            self.__shutdown_event__.set()
            
            # Add None to buffer to unblock the thread
            self.__buffer__.put(None)
            
            # Wait for thread to finish
            if self.__thread__ and self.__thread__.is_alive():
                self.__thread__.join(timeout=10.0)
                if self.__thread__.is_alive():
                    self.logger.warning("Thread did not terminate gracefully")
            
            # Save data and cleanup
            for symbol in self.symbols:
                try:
                    data = self.symbols[symbol]
                    self.exchange.unsubscribe_from_websocket(symbol, self.__time_frame__)
                    self.archiver.save(
                        self.exchange.get_exchange_name(),
                        symbol, self.data_type,
                        str(self.__time_frame__.value),
                        data)
                except Exception as e:
                    self.logger.error(f"Error saving data for {symbol}: {e}")
            
            WebsocketManager.close()
            self.logger.info("DataCenter shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during DataCenter shutdown: {e}")
            raise

    def __load_from_archive__(self, symbols):
        """Load data from archive with error handling."""
        for symbol in symbols:
            try:
                data = self.archiver.read(
                    self.exchange.get_exchange_name(),
                    symbol, self.data_type,
                    str(self.__time_frame__.value))
                self.__scan_and_backfill__(data, symbol)
            except Exception as e:
                self.logger.error(f"Failed to load archive for {symbol}: {e}")
                # Initialize with empty list if archive loading fails
                self.symbols[symbol] = []

    def __scan_and_backfill__(self, data, symbol):
        """Scan and backfill missing data with improved error handling."""
        try:
            current_datetime = self.exchange.get_exchange_info().first_data_datetime
            end_datetime = datetime.datetime.utcnow()

            if len(data) == 0:  # then there is no data at all. backfill everything
                self.symbols[symbol] = self.backfill(symbol, current_datetime, end_datetime, self.__time_frame__)
                return

            self.symbols[symbol] = []
            archived_data = sorted(data, key=lambda x: x.timestamp)

            index = 0
            total_length = len(archived_data)
            time_diff = datetime.timedelta(minutes=self.__time_frame__.value)

            self.__check_duplicate__(archived_data)

            while current_datetime < end_datetime and index < total_length:
                candle = archived_data[index]  # current candle
                candle_datetime = datetime.datetime.fromtimestamp(candle.timestamp / 1000)

                if candle_datetime == current_datetime:  # then we have the data
                    self.symbols[symbol].append(candle)
                    current_datetime += time_diff
                else:  # then we need to backfill
                    self.logger.debug(f"Candle timestamp {candle.timestamp}")
                    lost_data = self.backfill(symbol, current_datetime, candle_datetime, self.__time_frame__)
                    self.symbols[symbol].extend(lost_data)
                    current_datetime = candle_datetime + time_diff
                index += 1

            if current_datetime < end_datetime:  # we need to backfill until we reach the end of the data
                # to complete till the current time
                lost_data = self.backfill(symbol, current_datetime, end_datetime, self.__time_frame__)
                self.symbols[symbol].extend(lost_data)
                
        except Exception as e:
            self.logger.error(f"Failed to scan and backfill for {symbol}: {e}")
            self.symbols[symbol] = []

    def __check_duplicate__(self, archived_data):
        """Check for duplicate candles in archived data."""
        try:
            total_number_of_candles = len([candle.timestamp for candle in archived_data])
            total_number_of_distinct_candles = len({candle.timestamp for candle in archived_data})
            if total_number_of_candles != total_number_of_distinct_candles:
                self.logger.warning("There are duplicate candles in the archive. This will cause problems in the "
                                    f"back-filling. The total number of candles {total_number_of_candles} and the "
                                    f"total number of distinct candles {total_number_of_distinct_candles}")
        except Exception as e:
            self.logger.error(f"Error checking for duplicates: {e}")

    def request_candle(self, symbol: str, index: int = 0, reverse: bool = False) -> Optional[Candle]:
        """Request a specific candle with bounds checking."""
        try:
            if symbol not in self.symbols:
                return None

            data = self.symbols[symbol]
            if len(data) == 0:
                return None

            index = len(data) - 1 - index if reverse else index
            if index < 0 or index >= len(data):
                return None

            return data[index]
        except Exception as e:
            self.logger.error(f"Error requesting candle for {symbol}: {e}")
            return None

    def __initialize__(self):
        """Initialize the data center with error handling."""
        try:
            # retrieve all symbols from the exchange and back-fill if necessary
            symbols = self.fetch_product_list()

            # load data from archive if exists
            self.__load_from_archive__(symbols)

            # initialize indicators
            self.__initialize_indicators__()

            # start calculating indicators
            self.__start_calculating_indicators__()
            
            self.logger.info("DataCenter initialization complete")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize DataCenter: {e}")
            raise

    def __initialize_indicators__(self):
        """Initialize technical indicators."""
        try:
            for symbol in self.symbols.keys():
                # SMA
                sma = SimpleMovingAverage(symbol, self.request_candle)
                self.indicator_codes.append(sma.code)

                # EMA
                ema = ExponentialMovingAverage(symbol, self.request_candle)
                self.indicator_codes.append(ema.code)
                
            self.logger.info(f"Initialized {len(self.indicator_codes)} indicators")
        except Exception as e:
            self.logger.error(f"Failed to initialize indicators: {e}")

    def __start_calculating_indicators__(self):
        """Start calculating indicators for all symbols."""
        try:
            for indicator_code in self.indicator_codes:
                for symbol in self.symbols.keys():
                    indicator = TechnicalIndicator.get_instance(symbol, indicator_code)
                    self.__start_calculating_indicator__(indicator, symbol)
        except Exception as e:
            self.logger.error(f"Failed to start calculating indicators: {e}")

    def __start_calculating_indicator__(self, indicator: TechnicalIndicator, symbol: str) -> None:
        """Start calculating a specific indicator for a symbol."""
        try:
            for index, candle in enumerate(self.symbols[symbol]):
                indicator.calculate(candle, index)
        except Exception as e:
            self.logger.error(f"Failed to calculate indicator {indicator.code} for {symbol}: {e}")

    def __calculate_candle__(self, candle: Candle):
        """Calculate indicators for a new candle."""
        try:
            for indicator_code in self.indicator_codes:
                indicator: TechnicalIndicator = TechnicalIndicator.get_instance(candle.symbol, indicator_code)
                indicator.calculate(candle)
                indicator.print()
        except Exception as e:
            self.logger.error(f"Failed to calculate indicators for candle {candle.symbol}: {e}")

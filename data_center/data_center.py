import configparser
import datetime
import logging
from typing import List, Dict, Optional

from common_models.data_models.candle import Candle
from data_center.jobs.technical_indicator import TechnicalIndicator
from data_center.jobs.technical_indicators.sma import SimpleMovingAverage
from data_provider.exchange_collection.exchange import Exchange
from managers.archive_manager import ArchiveManager
from managers.websocket_manager import WebsocketManager
from startup import ServiceManager
from utils.singleton_metaclass.singleton import Singleton
from common_models.time_models import Interval
from queue import Queue
from threading import Thread


class DataCenter(metaclass=Singleton):
    def __init__(self):
        self.exchange: Exchange = ServiceManager.get_service("exchange")
        self.logger: logging.Logger = ServiceManager.get_service("logger")
        self.config: configparser.ConfigParser = ServiceManager.get_service("config")
        self.archiver: ArchiveManager = ServiceManager.get_service("archiver")

        self.__run_forever__: bool = True
        self.__backfill__: bool = False
        self.__thread__: Optional[Thread] = None
        self.data_type = "CANDLE"
        self.__time_frame__: Interval = Interval.ONE_MINUTE  # TODO: Get from config file

        self.symbols: Dict[str, List[Candle]] = {}
        self.__buffer__: Queue[Candle] = Queue()
        self.indicator_codes = []

        # register callbacks
        self.exchange.register_candle_callback(self.push_candle)

        # initialize
        self.__initialize__()

    def start(self):
        # start the thread for listening to the events
        self.__thread__ = Thread(target=self.run_forever, args=())
        self.__thread__.start()

        # subscribe to the websocket
        self.exchange.subscribe_to_websocket(list(self.symbols.keys()), self.__time_frame__)
        self.logger.info("DataCenter started")

    def fetch_product_list(self):
        # TODO: sorting option and limit will be added later from config file
        symbols = self.exchange.fetch_product_list()
        self.logger.info(f"Total symbols: {len(symbols)} in the exchange {self.exchange.get_exchange_name()}")
        return symbols

    def push_candle(self, candle: Candle):
        self.__buffer__.put(candle)

    def print_info(self, message, error_code):
        self.logger.info(message + " " + str(error_code))

    def backfill(self,
                 symbol: str,
                 start_date: datetime.datetime,
                 end_date: datetime.datetime,
                 interval: Interval) -> List[Candle]:
        self.logger.info(f"Back-filling {symbol} from {start_date} to {end_date} with interval {interval}...")
        candles = self.exchange.fetch_candle(symbol, start_date, end_date, interval)
        self.logger.info(f"Back-filling {symbol} from {start_date} to {end_date} with interval {interval}...Done")
        return candles

    def run_forever(self):
        while self.__run_forever__:
            candle = self.__buffer__.get()
            if candle is not None:
                self.symbols[candle.symbol].append(candle)
                self.logger.info(candle)
                self.__calculate_candle__(candle)

    def close(self):
        self.__run_forever__ = False
        self.__thread__.join(2)
        print("DataCenter closed")
        for symbol in self.symbols:
            data = self.symbols[symbol]
            self.exchange.unsubscribe_from_websocket(symbol, self.__time_frame__)
            self.archiver.save(
                self.exchange.get_exchange_name(),
                symbol, self.data_type,
                str(self.__time_frame__.value),
                data)
        print("DataCenter closed --")
        WebsocketManager.close()

    def __load_from_archive__(self, symbols):
        for symbol in symbols:
            data = self.archiver.read(
                self.exchange.get_exchange_name(),
                symbol,
                self.data_type,
                str(self.__time_frame__.value))

            if self.__backfill__:
                self.__scan_and_backfill__(data, symbol)

    def __scan_and_backfill__(self, data, symbol):
        """
        This method checks the data and fills the missing data with back-filling
        :param data: any kind of data read from archive and has a timestamp
        :param symbol: any valid symbol traded in an exchange
        :return: nothing
        """
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

        total_number_of_candles = len([candle.timestamp for candle in archived_data])
        total_number_of_distinct_candles = len({candle.timestamp for candle in archived_data})
        if total_number_of_candles != total_number_of_distinct_candles:
            self.logger.warning("There are duplicate candles in the archive. This will cause problems in the "
                                "back-filling")

        while current_datetime < end_datetime and index < total_length:
            candle = archived_data[index]  # current candle
            candle_datetime = datetime.datetime.utcfromtimestamp(candle.timestamp / 1000)

            if candle_datetime == current_datetime:  # then we have the data
                self.symbols[symbol].append(candle)
                current_datetime += time_diff
                self.logger.info(f"Found candle timestamp {candle.timestamp}")
            else:  # then we need to backfill
                self.logger.info(f"Candle timestamp {candle.timestamp}")
                lost_data = self.backfill(symbol, current_datetime, candle_datetime, self.__time_frame__)
                self.symbols[symbol].extend(lost_data)
                current_datetime = candle_datetime + time_diff
            index += 1

        if current_datetime < end_datetime:  # we need to backfill until we reach the end of the data
            # to complete till the current time
            lost_data = self.backfill(symbol, current_datetime, end_datetime, self.__time_frame__)
            self.symbols[symbol].extend(lost_data)

    def request_candle(self, symbol: str, index: int = 0, reverse: bool = False) -> Optional[Candle]:
        if symbol not in self.symbols:
            return None
        data = self.symbols[symbol]
        if len(data) == 0:
            return None
        index = len(data) - 1 - index if reverse else index
        if index < 0:
            return None
        return data[index]

    def __initialize__(self):
        # retrieve all symbols from the exchange and back-fill if necessary
        symbols = self.fetch_product_list()

        # load data from archive if exists
        self.__load_from_archive__(symbols)

        # initialize indicators
        self.__initialize_indicators__()

        # start calculating indicators
        self.__start_calculating_indicators__()

    def __initialize_indicators__(self):
        for symbol in self.symbols.keys():
            # SMA
            sma = SimpleMovingAverage(symbol, self.request_candle)
            self.indicator_codes.append(sma.code)

    def __start_calculating_indicators__(self):
        for indicator_code in self.indicator_codes:
            for symbol in self.symbols.keys():
                indicator = TechnicalIndicator.get_instance(symbol, indicator_code)
                self.__start_calculating_indicator__(indicator, symbol)

    def __start_calculating_indicator__(self, indicator: TechnicalIndicator, symbol: str) -> None:
        for index, candle in enumerate(self.symbols[symbol]):
            indicator.calculate(candle, index)

    def __calculate_candle__(self, candle: Candle):
        for indicator_code in self.indicator_codes:
            indicator: TechnicalIndicator = TechnicalIndicator.get_instance(candle.symbol, indicator_code)
            value = indicator.calculate(candle)
            indicator.print()

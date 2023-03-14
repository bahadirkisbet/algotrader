import configparser
import datetime
import logging
from typing import List, Dict, Optional

from common_models.data_models.candle import Candle
from data_provider.exchange_collection.exchange import Exchange
from managers.archive_manager import ArchiveManager
from startup import ServiceManager
from utils.singleton_metaclass.singleton import Singleton
from common_models.time_models import Interval
from queue import Queue
from multiprocessing import Lock
from threading import Thread


class DataCenter(metaclass=Singleton):
    def __init__(self):
        self.exchange: Exchange = ServiceManager.get_service("exchange")
        self.logger: logging.Logger = ServiceManager.get_service("logger")
        self.config: configparser.ConfigParser = ServiceManager.get_service("config")
        self.archiver: ArchiveManager = ServiceManager.get_service("archiver")

        self.__run_forever__: bool = True
        self.__thread__: Optional[Thread] = None
        self.data_type = "CANDLE"
        self.__time_frame__: Interval = Interval.ONE_MINUTE  # TODO: Get from config file

        self.symbols: Dict[str, List[Candle]] = {}
        self.application_lock: Lock = Lock()
        self.__buffer__: Queue[Candle] = Queue()

        # register callbacks
        self.exchange.register_candle_callback(self.push_candle)

    def start(self):
        # retrieve all symbols from the exchange and back-fill if necessary
        symbols = self.fetch_product_list()

        # load data from archive if exists
        self.load_from_archive(symbols)

        # start the thread for listening to the events
        self.__thread__ = Thread(target=self.run_forever, args=())
        self.__thread__.start()

        # subscribe to the websocket
        self.exchange.subscribe_to_websocket(symbols, self.__time_frame__)

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
            if candle.symbol not in self.symbols:
                self.symbols[candle.symbol] = []
            self.symbols[candle.symbol].append(candle)
            self.logger.info(candle)

    def close(self):
        self.__run_forever__ = False
        self.__thread__.join()
        for symbol in self.symbols:
            data = self.symbols[symbol]
            self.exchange.unsubscribe_from_websocket(symbol, self.__time_frame__)
            self.archiver.save(
                self.exchange.get_exchange_name(),
                symbol, self.data_type,
                str(self.__time_frame__.value),
                data)

    def load_from_archive(self, symbols):
        for symbol in symbols:
            data = self.archiver.read(
                self.exchange.get_exchange_name(),
                symbol,
                self.data_type,
                str(self.__time_frame__.value))

            self.scan_and_backfill(data, symbol)

    def scan_and_backfill(self, data, symbol):
        """
        This method checks the data and fills the missing data with back-filling
        :param data: any kind of data read from archive and has a timestamp
        :param symbol: any valid symbol traded in an exchange
        :return: nothing
        """
        current_datetime = self.exchange.get_exchange_info().first_data_datetime
        end_datetime = datetime.datetime.utcnow()

        if len(data) == 0:
            self.symbols[symbol] = self.backfill(symbol, current_datetime, end_datetime, self.__time_frame__)
            return

        self.symbols[symbol] = []
        archived_data = sorted(data, key=lambda x: x.timestamp)

        index = 0
        total_length = len(archived_data)

        while current_datetime < end_datetime and index < total_length:
            candle = archived_data[index]
            current_ts = int(current_datetime.timestamp() * 1000)

            if candle.timestamp == current_ts:
                self.symbols[symbol].append(candle)
                current_datetime += datetime.timedelta(minutes=self.__time_frame__.value)
            else:
                candle_datetime = datetime.datetime.fromtimestamp(candle.timestamp / 1000)
                lost_data = self.backfill(symbol, current_datetime, candle_datetime, self.__time_frame__)
                self.symbols[symbol].extend(lost_data)
                current_datetime = candle_datetime
            index += 1

        if current_datetime < end_datetime:
            lost_data = self.backfill(symbol, current_datetime, end_datetime, self.__time_frame__)
            self.symbols[symbol].extend(lost_data)


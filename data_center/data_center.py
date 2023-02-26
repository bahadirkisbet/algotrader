import configparser
import datetime
import logging
from typing import List, Dict

from common_models.data_models.candle import Candle
from data_provider.exchange_collection.exchange_base import ExchangeBase
from managers.archive_manager import ArchiveManager
from startup import ServiceManager
from utils.singleton_metaclass.singleton import Singleton
from common_models.time_models import Interval
from queue import Queue
from multiprocessing import Lock
from threading import Thread


class DataCenter(metaclass=Singleton):
    def __init__(self):
        self.__buffer__: Queue[Candle] = Queue()
        self.exchange: ExchangeBase = ServiceManager.get_service("exchange")
        self.logger: logging.Logger = ServiceManager.get_service("logger")
        self.config: configparser.ConfigParser = ServiceManager.get_service("config")
        self.archiver: ArchiveManager = ServiceManager.get_service("archiver")
        self.symbols: Dict[str, List[Candle]] = {}
        self.application_lock: Lock = Lock()
        self.__is_running__: bool = True
        self.__time_frame__: Interval = Interval.ONE_MINUTE
        self.__thread__: Thread = None

        # register callbacks
        self.exchange.register_candle_callback(self.push_candle)

    def start(self):
        symbols = self.exchange.fetch_product_list()
        self.logger.info(f"Total symbols: {len(symbols)}")
        self.exchange.subscribe_to_websocket(symbols, self.__time_frame__)
        self.__thread__ = Thread(target=self.run_forever, args=())
        self.__thread__.start()

    def push_candle(self, candle: Candle):
        self.__buffer__.put(candle)

    def print_info(self, message, error_code):
        self.logger.info(message + " " + str(error_code))

    def backfill(self,
                 symbols: List[str],
                 start_date: datetime.datetime,
                 end_date: datetime.datetime,
                 interval: Interval) -> None:
        pass

        for symbol in symbols:
            candles = self.exchange.fetch_candle(symbol, start_date, end_date, interval)
            for candle in candles:
                self.push_candle(candle)

    def run_forever(self):
        while self.__is_running__:
            candle = self.__buffer__.get()
            if candle.symbol not in self.symbols:
                self.symbols[candle.symbol] = []
            self.symbols[candle.symbol].append(candle)
            self.logger.info(candle)

    def close(self):
        self.__is_running__ = False
        self.__thread__.join()
        for symbol in self.symbols:
            data = self.symbols[symbol]
            self.exchange.unsubscribe_from_websocket(symbol, self.__time_frame__)
            self.archiver.save(self.exchange.name, symbol, "CANDLE", str(self.__time_frame__.value), data)

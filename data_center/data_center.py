import configparser
import datetime
import logging
from typing import List, Dict

from common_models.data_models.candle import Candle
from data_provider.exchange_collection.exchange_base import ExchangeBase
from startup import ServiceManager
from utils.singleton_metaclass.singleton import Singleton
from common_models.time_models import Interval
from queue import Queue
from multiprocessing import Lock


class DataCenter(metaclass=Singleton):
    def __init__(self):
        self.__buffer__: Queue[Candle] = Queue()
        self.exchange: ExchangeBase = ServiceManager.get_service("exchange")
        self.logger: logging.Logger = ServiceManager.get_service("logger")
        self.config: configparser.ConfigParser = ServiceManager.get_service("config")
        self.symbols: Dict[str, List[Candle]] = {}
        self.application_lock = Lock()

        # register callbacks
        self.exchange.register_candle_callback(self.push_candle)

    def start(self):
        symbols = self.exchange.fetch_product_list()
        self.logger.info(f"Total symbols: {len(symbols)}")
        self.exchange.subscribe_to_websocket(symbols, Interval.ONE_MINUTE)
        self.run_forever()

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

    def run_forever(self):
        while True:
            candle = self.__buffer__.get()
            if candle.symbol not in self.symbols:
                self.symbols[candle.symbol] = []
            self.symbols[candle.symbol].append(candle)
            self.logger.info(candle)

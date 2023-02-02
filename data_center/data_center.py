import datetime
import logging
from typing import List

from common_models.data_models.candle import Candle
from data_provider.exchange_collection.exchange_base import ExchangeBase
from utils.singleton_metaclass.singleton import Singleton
from common_models.time_models import Interval


class DataCenter(metaclass=Singleton):
    def __init__(self, logger: logging.Logger, exchange: ExchangeBase):
        self.__buffer__: List[Candle] = []
        self.exchange = exchange
        self.logger = logger

    def start(self):
        symbols = self.exchange.fetch_product_list()
        self.logger.info(f"Total symbols: {len(symbols)}")
        self.exchange.subscribe_to_websocket(symbols, Interval.FIVE_MINUTES)

    def push_candle(self, candle: Candle):
        self.__buffer__.append(candle)

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

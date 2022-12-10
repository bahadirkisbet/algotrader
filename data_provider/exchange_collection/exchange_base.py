import configparser
import logging
from abc import abstractmethod, ABC
from datetime import datetime
from common_models.time_models import Interval
from typing import List


class ExchangeBase(ABC):

    def __init__(self, config: configparser.ConfigParser, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.__development_mode__ = config["DEFAULT"].getboolean("development_mode")

    @abstractmethod
    def _on_message_(self, message):
        pass

    @abstractmethod
    def _on_error_(self, error):
        pass

    @abstractmethod
    def _on_close_(self, close_status_code, close_msg):
        pass

    @abstractmethod
    def _on_open_(self):
        pass

    @abstractmethod
    def fetch_product_list(self) -> List[str]:
        """
        :return: Retrieves trade-able product list of the relevant exchange
        """
        pass

    @abstractmethod
    def fetch_candle(self, symbol: str, startDate: datetime, endDate: datetime, interval: Interval) -> list:
        """
            Fetches candle data from exchange. In general, it is meant to do it concurrently.
            
                - symbol: str -> Symbol of the asset in the corresponding exchange.
                    - Example: "BTC/USDT", "ETH/USDT", "LTC/USDT", "BTCUSDT", "ETHUSDT", "LTCUSDT"
                - startDate: datetime -> Start date of the candle data.
                    - Example: datetime(2020, 1, 1, 0, 0, 0)
                - endDate: datetime -> End date of the candle data.
                    - Example: datetime(2022, 1, 1, 0, 0, 0)
                - interval: str -> Interval of the candle data.
                    - Example: "1m", "5m", "1h", "1d"
        """
        pass

    @abstractmethod
    def subscribe_to_websocket(self, symbols: List[str], interval: Interval) -> None:
        """
            Subscribes to websocket to get realtime data.
            
                - symbol: str -> Symbol of the asset in the corresponding exchange.
                    - Example: "BTC/USDT", "ETH/USDT", "LTC/USDT", "BTCUSDT", "ETHUSDT", "LTCUSDT"
                - interval: Interval -> Interval of the candle data.
                    - Example: "1m", "5m", "1h", "1d"
        """
        pass

    @abstractmethod
    def unsubscribe_from_websocket(self, symbol: str, interval: Interval) -> None:
        """
            Unsubscribes from websocket to stop getting realtime data.
            
                - symbol: str -> Symbol of the asset in the corresponding exchange.
                    - Example: "BTC/USDT", "ETH/USDT", "LTC/USDT", "BTCUSDT", "ETHUSDT", "LTCUSDT"
                - interval: Interval -> Interval of the candle data.
                    - Example: "1m", "5m", "1h", "1d"
        """
        pass

    def interval_to_granularity(self, interval: Interval) -> str:
        """
            Converts interval to the requested granularity of an exchange.
            
                - interval: Interval -> Interval of the candle data.
                    - Example: "1m", "5m", "1h", "1d"
                    That is,
                    - Interval.ONE_MINUTES -> "1m"
                    - Interval.FIVE_MINUTES -> "5m"
                    - Interval.FIFTEEN_MINUTES -> "15m"
                    - Interval.ONE_HOUR -> "1h"

        """
        pass

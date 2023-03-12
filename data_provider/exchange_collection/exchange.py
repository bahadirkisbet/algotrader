import datetime
from abc import abstractmethod, ABC
from typing import List

from common_models.exchange_info import ExchangeInfo
from common_models.sorting_option import *
from common_models.time_models import Interval


class Exchange(ABC):

    @abstractmethod
    def fetch_product_list(self, sortingOption: SortingOption = None, limit: int = -1) -> List[str]:
        """
        :return: Retrieves trade-able product list of the relevant exchange
        """
        pass

    @abstractmethod
    def fetch_candle(self,
                     symbol: str,
                     startDate: datetime.datetime,
                     endDate: datetime.datetime,
                     interval: Interval) -> list:
        """
            Fetches candle data from exchange. In general, it is meant to do it concurrently.

            :param symbol: str -> Symbol of the asset in the corresponding exchange.
                Example: "BTC/USDT", "ETH/USDT", "LTC/USDT", "BTCUSDT", "ETHUSDT", "LTCUSDT"
            :param startDate: datetime -> Start date of the candle data.
                Example: datetime(2020, 1, 1, 0, 0, 0)
            :param endDate: datetime -> End date of the candle data.
                Example: datetime(2022, 1, 1, 0, 0, 0)
            :param interval: str -> Interval of the candle data.
                Example: "1m", "5m", "1h", "1d"
        """
        pass

    @abstractmethod
    def subscribe_to_websocket(self, symbols: List[str], interval: Interval) -> None:
        """
            Subscribes to websocket to get realtime data.

                :param symbols: List[str] -> Symbol of the asset in the corresponding exchange.
                    - Example: "BTC/USDT", "ETH/USDT", "LTC/USDT", "BTCUSDT", "ETHUSDT", "LTCUSDT"
                :param interval: Interval -> Interval of the candle data.
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

    @abstractmethod
    def register_candle_callback(self, callback):
        pass

    @abstractmethod
    def get_exchange_name(self) -> str:
        pass

    @abstractmethod
    def get_exchange_info(self) -> ExchangeInfo:
        pass

import datetime
from abc import ABC, abstractmethod
from typing import Callable, List

from models.exchange_info import ExchangeInfo
from models.sorting_option import SortingOption
from models.time_models import Interval


class Exchange(ABC):
    """Abstract base class for all exchange implementations."""
    
    @abstractmethod
    async def fetch_product_list(self, sortingOption: SortingOption = None, limit: int = -1) -> List[str]:
        """
        :return: Retrieves trade-able product list of the relevant exchange
        """
        pass
    
    @abstractmethod
    async def fetch_ohlcv(self,
                          symbol: str,
                          startDate: datetime.datetime,
                          endDate: datetime.datetime,
                          interval: Interval) -> List:
        """
        Fetches OHLCV data from exchange asynchronously.
        
        :param symbol: str -> Symbol of the asset in the corresponding exchange.
        :param startDate: datetime -> Start date for the data.
        :param endDate: datetime -> End date for the data.
        :param interval: Interval -> Time interval for the data.
        :return: List of OHLCV data.
        """
        pass
    
    @abstractmethod
    async def subscribe_to_websocket(self, symbols: List[str], interval: Interval) -> None:
        """
        Subscribes to websocket to get realtime data.
        
        :param symbols: Symbol of the asset in the corresponding exchange.
            - Example: "BTC/USDT", "ETH/USDT", "LTC/USDT", "BTCUSDT", "ETHUSDT", "LTCUSDT"
        - interval: Interval of the candle data.
            - Example: "1m", "5m", "1h", "1d"
        """
        pass
    
    @abstractmethod
    async def unsubscribe_from_websocket(self, symbol: str, interval: Interval) -> None:
        """
        Unsubscribes from websocket to stop getting realtime data.
        
        :param symbol: Symbol of the asset in the corresponding exchange.
        :param interval: Interval of the candle data.
        """
        pass
    
    @abstractmethod
    def register_candle_callback(self, callback: Callable) -> None:
        """Register a callback function for candle data updates."""
        pass
    
    @abstractmethod
    def get_exchange_name(self) -> str:
        """Get the name of the exchange."""
        pass
    
    @abstractmethod
    def get_exchange_info(self) -> ExchangeInfo:
        """Get exchange information."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the exchange connection gracefully."""
        pass

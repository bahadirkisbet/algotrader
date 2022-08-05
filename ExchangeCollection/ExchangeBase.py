from abc import abstractmethod, ABC
from datetime import datetime

from CommonModels.DataModels import Interval

class ExchangeBase(ABC):

    @abstractmethod
    def fetch_candle(self, symbol: str, startDate: datetime, endDate: datetime, interval: str) -> list:
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
    def subscribe_to_websocket(self, symbol: str, interval: Interval) -> None:
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
        
    
    def interval_to_granularity(self, interval: Interval) -> int:
        """
            Converts interval to the requested granularity of an exchange.
            
                - interval: Interval -> Interval of the candle data.
                    - Example: Let's say exchange says that give me the intervals in seconds,
                        - "1m" -> 60
                        - "5m" -> 300
                        - "1h" -> 3600
                        - "1d" -> 86400
        """
        pass
    

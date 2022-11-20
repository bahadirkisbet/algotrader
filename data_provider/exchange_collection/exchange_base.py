import configparser
import logging
from abc import abstractmethod, ABC
from datetime import datetime
from common_models.time_models import Interval
from typing import List
import json
import websocket


class ExchangeBase(ABC):

    def __init__(self, config: configparser.ConfigParser, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.__data_callbacks__ = list()
        self.__error_callbacks__ = list()
        self._websocket_dict_ = dict()
        self._websocket_connection_count_ = dict()
        self._max_connection_limit_ = config["EXCHANGE"]["max_connection_limit"]

    def register_callbacks(self, data_callbacks: list, error_callbacks=None) -> None:
        for data_callback in data_callbacks:
            self.__data_callbacks__.append(data_callback)
        if error_callbacks is not None:
            for error_callback in error_callbacks:
                self.__error_callbacks__.append(error_callback)

    def _create_websocket_connection_(self, address, port=None):
        socket_name = f"SOCKET_{len(self._websocket_dict_)}"
        if socket_name in self._websocket_connection_count_ and \
                self._websocket_connection_count_[socket_name] < self._max_connection_limit_:
            # there is an available socket, use it
            self._websocket_connection_count_[socket_name] += 1
            return socket_name

        def on_message(ws: websocket.WebSocketApp, message):
            msg = json.loads(message)
            self.logger.info("Message has received: %s" % msg)
            # publish to callbacks
            for callback in self.__data_callbacks__:
                callback(msg)

        def on_error(ws: websocket.WebSocketApp, error):
            self.logger.error(error)
            for callback in self.__error_callbacks__:
                callback(error)

        def on_close(ws: websocket.WebSocketApp, close_status_code, close_msg):
            self.logger.warning("websocket is closed", close_status_code, close_msg)

        def on_open(ws: websocket.WebSocketApp):
            self.logger.info("Websocket connection is done to %s" % ws.url)

        url = address
        if port is not None:
            url += ":" + str(port)

        socket = websocket.WebSocketApp(
            url=url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open,
        )
        socket_name = f"SOCKET_{len(self._websocket_dict_) + 1}"
        self._websocket_dict_[socket_name] = socket
        self._websocket_connection_count_[socket_name] = 1
        print(socket.run_forever())
        return socket_name

    @abstractmethod
    def fetch_product_list(self):
        """
        :return: Retrieves trade-able product list of the relevant exchange
        """
        pass

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

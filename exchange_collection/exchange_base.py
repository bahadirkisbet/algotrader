import configparser
import logging
from abc import abstractmethod, ABC
from datetime import datetime
from common_models.DataModels import Interval
import json
import websocket


class ExchangeBase(ABC):

    def __init__(self, config: configparser.ConfigParser, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.__data_callbacks__ = list()
        self.__error_callbacks__ = list()
        self.__websocket_dict__ = dict()

    def register_callbacks(self, data_callbacks: list, error_callbacks=None) -> None:
        for data_callback in data_callbacks:
            self.__data_callbacks__.append(data_callback)
        if error_callbacks is not None:
            for error_callback in error_callbacks:
                self.__error_callbacks__.append(error_callback)

    def __create_websocket_connection__(self, address, port=None):
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

        url = "wss://" + address
        if port is not None:
            url += ":" + str(port)

        socket = websocket.WebSocketApp(
            url=url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open,
        )
        socket_name = f"SOCKET_{len(self.__websocket_dict__) + 1}"
        self.__websocket_dict__[socket_name] = socket
        socket.run_forever()
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
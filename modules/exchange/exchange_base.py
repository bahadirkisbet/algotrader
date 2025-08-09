import configparser
import datetime
import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from data_provider.exchange_collection.exchange import Exchange

from modules.websocket import WebsocketManager
from models.exchange_info import ExchangeInfo
from models.time_models import Interval


class ExchangeBase(Exchange, ABC):
    def __init__(self):
        from utils.dependency_injection_container import get
        self.config: configparser.ConfigParser = get(configparser.ConfigParser)
        self.logger: logging.Logger = get(logging.Logger)
        self.development_mode: bool = self.config["DEFAULT"].getboolean("development_mode")
        self.symbol_to_websocket_mapping = {}
        self.name: str = "NotSet"
        self.websocket_url: str = "NotSet"
        self.api_url: str = "NotSet"
        self.api_endpoints: dict = {}
        self.candle_callback: callable = None
        self.first_data_date: datetime.datetime = datetime.datetime(2020, 1, 1, 0, 0, 0)
        self.exchange_info: Optional[ExchangeInfo] = None

    @abstractmethod
    def handle_websocket_message(self, message):
        pass

    def handle_websocket_error(self, error):
        self.logger.info(error)

    # noinspection PyUnusedLocal
    def handle_websocket_close(self, close_status_code, close_msg):
        self.logger.info(f"Socket closed with the following message: {close_msg} and status code: {close_status_code}")

    def handle_websocket_open(self):
        self.logger.info("opened")

    @abstractmethod
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

    def subscribe_to_websocket(self, symbols: List[str], interval: Interval) -> None:
        assert self.websocket_url is not None, "websocket_url not defined"
        websocket_name = WebsocketManager.create_websocket_connection(
            address=self.websocket_url,
            port=None,
            on_message=self.handle_websocket_message,
            on_error=self.handle_websocket_error,
            on_close=self.handle_websocket_close,
            on_open=self.handle_websocket_open)
        WebsocketManager.start_connection(websocket_name)
        socket = WebsocketManager.WebsocketDict[websocket_name]

        self.logger.info(f"Subscribing to {symbols} at {websocket_name}")
        for symbol in symbols:
            self.symbol_to_websocket_mapping[symbol] = websocket_name
            socket.send(self.prepare_subscribe_message(symbol, interval))
            self.logger.info(f"Subscribed to {symbol} at {websocket_name}")

    def unsubscribe_from_websocket(self, symbol: str, interval: Interval) -> None:
        socket_name = self.symbol_to_websocket_mapping[symbol]
        socket = WebsocketManager.WebsocketDict[socket_name]
        socket.send(self.prepare_unsubscribe_message(symbol, interval))
        WebsocketManager.end_connection(socket_name)

    @abstractmethod
    def get_max_candle_limit(self) -> int:
        """
            Returns the maximum number of candles that can be fetched in a single request.
        """
        pass

    @abstractmethod
    def convert_datetime_to_exchange_timestamp(self, dt: datetime.datetime) -> str:
        """
            Converts datetime to exchange timestamp.
        """
        pass

    # Helper methods for child classes

    def register_candle_callback(self, callback):
        self.candle_callback = callback

    def get_exchange_name(self) -> str:
        return self.name

    def get_exchange_info(self) -> ExchangeInfo:
        return self.exchange_info

    @abstractmethod
    def prepare_subscribe_message(self, symbol, interval):
        pass

    @abstractmethod
    def prepare_unsubscribe_message(self, symbol, interval):
        pass

import configparser
import datetime
import logging
from typing import Optional, List

from models.exchange_info import ExchangeInfo
from models.time_models import Interval
from data_provider.exchange_collection.exchange import Exchange
from abc import ABC, abstractmethod

from managers.service_manager import ServiceManager
from managers.websocket_manager import WebsocketManager


class ExchangeBase(Exchange, ABC):
    def __init__(self):
        self.config: configparser.ConfigParser = ServiceManager.get_service("config")
        self.logger: logging.Logger = ServiceManager.get_service("logger")
        self.__development_mode__: bool = self.config["DEFAULT"].getboolean("development_mode")
        self.__symbol_to_ws__ = {}
        self.name: str = "NotSet"
        self.websocket_url: str = "NotSet"
        self.api_url: str = "NotSet"
        self.api_endpoints: dict = {}
        self.candle_callback: callable = None
        self.first_data_date: datetime.datetime = datetime.datetime(2020, 1, 1, 0, 0, 0)
        self.exchange_info: Optional[ExchangeInfo] = None

    @abstractmethod
    def _on_message_(self, message):
        pass

    def _on_error_(self, error):
        self.logger.info(error)

    # noinspection PyUnusedLocal
    def _on_close_(self, close_status_code, close_msg):
        self.logger.info(f"Socket closed with the following message: {close_msg} and status code: {close_status_code}")

    def _on_open_(self):
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
            on_message=self._on_message_,
            on_error=self._on_error_,
            on_close=self._on_close_,
            on_open=self._on_open_)
        WebsocketManager.start_connection(websocket_name)
        socket = WebsocketManager.WebsocketDict[websocket_name]

        self.logger.info(f"Subscribing to {symbols} at {websocket_name}")
        for symbol in symbols:
            self.__symbol_to_ws__[symbol] = websocket_name
            socket.send(self.__prepare_subscribe_message__(symbol, interval))
            self.logger.info(f"Subscribed to {symbol} at {websocket_name}")

    def unsubscribe_from_websocket(self, symbol: str, interval: Interval) -> None:
        socket_name = self.__symbol_to_ws__[symbol]
        socket = WebsocketManager.WebsocketDict[socket_name]
        socket.send(self.__prepare_unsubscribe_message__(symbol, interval))
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
        if self.exchange_info is None:
            self.exchange_info = ExchangeInfo(
                self.name,
                self.first_data_date)
        return self.exchange_info

    @abstractmethod
    def __prepare_subscribe_message__(self, symbol, interval):
        pass

    @abstractmethod
    def __prepare_unsubscribe_message__(self, symbol, interval):
        pass

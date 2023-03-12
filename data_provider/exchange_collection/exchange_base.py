import configparser
import datetime
import logging
from typing import Optional

from common_models.exchange_info import ExchangeInfo
from common_models.time_models import Interval
from data_provider.exchange_collection.exchange import Exchange
from abc import ABC, abstractmethod

from managers.service_manager import ServiceManager


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
    def _create_url_list_(self,
                          startDate: datetime.datetime,
                          endDate: datetime.datetime,
                          interval: Interval,
                          symbol: str):
        assert "fetch_candle" in self.api_endpoints, "`fetch_candle` endpoint is not defined in api_endpoints"
        assert self.interval_to_granularity(interval) is not None, "`interval_to_granularity` is not implemented"
        assert self.get_max_candle_limit() is not None, "`get_max_candle_limit` is not implemented"
        assert self.convert_datetime_to_exchange_timestamp(
            startDate) is not None, "`convert_datetime_to_exchange_timestamp` is not implemented"

        url_list = []
        current_date = startDate
        limit = self.get_max_candle_limit()
        while current_date <= endDate:
            next_date = current_date + datetime.timedelta(minutes=interval.value * limit)
            url = self.api_url + self.api_endpoints["fetch_candle"].format(
                symbol,
                self.interval_to_granularity(interval),
                self.convert_datetime_to_exchange_timestamp(current_date),
                self.convert_datetime_to_exchange_timestamp(next_date),
                limit
            )
            url_list.append([url])
            current_date = next_date
        return url_list

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

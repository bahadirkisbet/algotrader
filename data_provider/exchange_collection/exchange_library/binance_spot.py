import json
import multiprocessing
import multiprocessing.pool
from typing import List

import requests

from common_models.data_models.candle import Candle
from common_models.exchange_type import ExchangeType
from common_models.sorting_option import SortingOption, SortBy
from managers.websocket_manager import WebsocketManager
from data_provider.exchange_collection.exchange_base import *
from threading import Semaphore


class Binance(ExchangeBase):
    """
        Binance is a cryptocurrency exchange.
            - https://www.binance.com/
    """

    def __init__(self):
        super().__init__()
        self.name: str = "Binance"
        self.request_lock: Semaphore = Semaphore(100)
        self.exchange_type: ExchangeType = ExchangeType.SPOT
        self.websocket_url: str = "wss://stream.binance.com:9443/ws"
        self.api_url: str = "https://api.binance.com"
        self.api_endpoints: dict = {
            "fetch_candle": "/api/v3/klines?symbol={}&interval={}&startTime={}&endTime={}&limit={}",
            "fetch_product_list": "/api/v3/ticker/24hr"
        }
        self.first_data_date = datetime.datetime(2017, 8, 14, 0, 0, 0, 0)

    def fetch_product_list(self, sortingOption: SortingOption = None, limit: int = -1) -> List[str]:
        assert "fetch_product_list" in self.api_endpoints, "`fetch_product_list` endpoint not defined"

        if self.__development_mode__:
            return ["BTCUSDT"]

        url = self.api_url + self.api_endpoints["fetch_product_list"]
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception("Error while fetching product list")
        # first filter by status == TRADING then select only the symbol
        data = response.json()

        if sortingOption is not None:
            data = self.__apply_sorting_options__(data, sortingOption)

        if limit > 0:
            data = data[:limit]

        return [product["symbol"] for product in data]

    @staticmethod
    def __apply_sorting_options__(data, sortingOption):
        match sortingOption.sort_by:
            case SortBy.SYMBOL:
                data = sorted(data, key=lambda x: x["symbol"], reverse=sortingOption.sort_order.value)
            case SortBy.PRICE:
                data = sorted(data, key=lambda x: x["lastPrice"], reverse=sortingOption.sort_order.value)
            case SortBy.VOLUME:
                data = sorted(data, key=lambda x: x["volume"], reverse=sortingOption.sort_order.value)
            case SortBy.CHANGE:
                data = sorted(data, key=lambda x: x["priceChange"], reverse=sortingOption.sort_order.value)
            case SortBy.CHANGE_PERCENT:
                data = sorted(data, key=lambda x: x["priceChangePercent"], reverse=sortingOption.sort_order.value)
            case _:
                pass
        return data

    def fetch_candle(self, symbol: str, startDate: datetime, endDate: datetime, interval: Interval) -> List[Candle]:
        assert "fetch_candle" in self.api_endpoints, "fetch_candle endpoint not defined"
        assert self.api_url is not None, "api_url not defined"

        url_list = self._create_url_list_(startDate, endDate, interval, symbol)

        with multiprocessing.pool.ThreadPool() as pool:
            response_list = pool.starmap(self.__make_request__, url_list)
            result = [item for response in response_list if response is not None for item in response]
            for candle in result:
                candle.symbol = symbol
        return result

    def __make_request__(self, url):
        self.logger.info(f"Fetching candle data from {url} with the semaphore value {self.request_lock._value}")
        self.request_lock.acquire()  # lock
        response = requests.get(url)
        self.request_lock.release()  # unlock
        if response.status_code != 200:
            self.logger.warning(f"Error while fetching candle - {response.status_code} - {response.text} - {url}")
            return None
        json_data = response.json()

        return [Candle(
            symbol="",
            timestamp=int(item[0]),
            open=float(item[1]),
            high=float(item[2]),
            low=float(item[3]),
            close=float(item[4]),
            volume=float(item[5]),
            trade_count=int(item[8])
        ) for item in json_data]

    # SOCKET RELATED METHODS #

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

    def __prepare_subscribe_message__(self, symbol: str, interval: Interval) -> str:
        return json.dumps({
            "method": "SUBSCRIBE",
            "params": [f"{symbol.lower()}@kline_{self.interval_to_granularity(interval)}"],
            "id": 1
        })

    def __prepare_unsubscribe_message__(self, symbol: str, interval: Interval) -> str:
        return json.dumps({
            "method": "UNSUBSCRIBE",
            "params": [f"{symbol.lower()}@kline_{self.interval_to_granularity(interval)}"],
            "id": 1
        })

    def unsubscribe_from_websocket(self, symbol: str, interval: Interval) -> None:
        socket_name = self.__symbol_to_ws__[symbol]
        socket = WebsocketManager.WebsocketDict[socket_name]
        socket.send(self.__prepare_unsubscribe_message__(symbol, interval))
        WebsocketManager.end_connection(socket_name)

    def _on_message_(self, message):
        print(message)  # to avoid actual logging, we may print this, but it will be printed in the console
        data = message
        event_time = data["E"]
        candle_data = data["k"]
        if event_time >= candle_data["T"]:
            candle = Candle(
                symbol=data["s"],
                timestamp=candle_data["t"],
                open=float(candle_data["o"]),
                high=float(candle_data["h"]),
                low=float(candle_data["l"]),
                close=float(candle_data["c"]),
                volume=float(candle_data["v"]),
                trade_count=int(candle_data["n"])
            )
            self.logger.info(candle)
            self.candle_callback(candle)

    def _on_error_(self, error):
        self.logger.info(error)

    def _on_close_(self, close_status_code, close_msg):
        self.logger.info("Socket closed")

    def _on_open_(self):
        self.logger.info("opened")

    # GENERIC METHODS #
    def interval_to_granularity(self, interval: Interval) -> object:
        match interval:
            case Interval.ONE_MINUTE:
                return "1m"
            case Interval.FIVE_MINUTES:
                return "5m"
            case Interval.FIFTEEN_MINUTES:
                return "15m"
            case Interval.ONE_HOUR:
                return "1h"
            case Interval.ONE_DAY:
                return "1d"
            case _:
                raise Exception("Interval not supported")

    def get_max_candle_limit(self) -> int:
        return 1000

    def convert_datetime_to_exchange_timestamp(self, dt: datetime.datetime) -> str:
        return str(int(dt.timestamp() * 1000))

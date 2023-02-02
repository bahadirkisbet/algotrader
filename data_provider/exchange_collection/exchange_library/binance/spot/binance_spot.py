import multiprocessing
import multiprocessing.pool

import requests

from common_models.data_models.candle import Candle
from common_models.exchange_type import ExchangeType
from utils.websocket_manager.websocket_manager import WebsocketManager
from ..binance_base import *
from threading import Semaphore


class BinanceSpot(BinanceBase):
    """
        Binance is a cryptocurrency exchange.
            - https://www.binance.com/
    """
    exchange_type: ExchangeType = ExchangeType.SPOT
    websocket_url: str = "wss://stream.binance.com:9443/ws"
    api_url = "https://api.binance.com"
    api_endpoints: dict = {
        "fetch_candle": "/api/v3/klines?symbol={symbol}&interval={interval}&startTime={start}&endTime={end}&limit=1000",
        "fetch_product_list": "/api/v3/exchangeInfo"
    }

    def __init__(self):
        super().__init__()
        self.request_lock = Semaphore(50)

    def fetch_product_list(self) -> List[str]:
        assert "fetch_product_list" in self.api_endpoints, "`fetch_product_list` endpoint not defined"

        if self.__development_mode__:
            return ["BTCUSDT"]

        url = self.api_url + self.api_endpoints["fetch_product_list"]
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception("Error while fetching product list")
        json_data = response.json()
        # first filter by status == TRADING then select only the symbol
        return [product["symbol"] for product in json_data["symbols"] if product["status"] == "TRADING"]

    def fetch_candle(self, symbol: str, startDate: datetime, endDate: datetime, interval: Interval) -> List[Candle]:
        assert "fetch_candle" in self.api_endpoints, "fetch_candle endpoint not defined"
        assert self.api_url is not None, "api_url not defined"

        url_list = self._create_url_list_(endDate, interval, startDate, symbol)

        with multiprocessing.pool.ThreadPool() as pool:
            response_list = pool.starmap(self.__make_request__, url_list)
            result = [item for response in response_list if response is not None for item in response]

        return result

    def __make_request__(self, url):
        self.logger.info(f"Fetching candle data from {url} at {self.request_lock}")
        self.request_lock.acquire()  # lock
        response = requests.get(url)
        self.request_lock.release()  # unlock
        if response.status_code != 200:
            self.logger.warning(f"Error while fetching candle - {response.status_code} - {response.text} - {url}")
            return None
        json = response.json()

        return [Candle(
            timestamp=int(item[0]),
            open=float(item[1]),
            high=float(item[2]),
            low=float(item[3]),
            close=float(item[4]),
            volume=float(item[5]),
            trade_count=int(item[8])
        ) for item in json]

    # SOCKET RELATED METHODS #

    def subscribe_to_websocket(self, symbols: List[str], interval: Interval) -> None:
        websocket_name = WebsocketManager.create_websocket_connection(
            address=self.websocket_url,
            port=None,
            on_message=self._on_message_,
            on_error=self._on_error_,
            on_close=self._on_close_,
            on_open=self._on_open_)
        WebsocketManager.start_connection(websocket_name)
        socket = WebsocketManager.WebsocketDict[websocket_name]
        for symbol in symbols:
            self.__symbol_to_ws__[symbol] = websocket_name
            socket.send(self.__prepare_subscribe_message__(symbol, interval))

    @staticmethod
    def __prepare_subscribe_message__(symbol: str, interval: Interval) -> str:
        return f"{{\"method\": \"SUBSCRIBE\", \"params\": [\"{symbol.lower()}@kline_{interval.value}\"], \"id\": 1}}"

    @staticmethod
    def __prepare_unsubscribe_message__(symbol: str, interval: Interval) -> str:
        return f"{{\"method\": \"UNSUBSCRIBE\", \"params\": [\"{symbol.lower()}@kline_{interval.value}\"], \"id\": 1}}"

    def unsubscribe_from_websocket(self, symbol: str, interval: Interval) -> None:
        socket_name = self.__symbol_to_ws__[symbol]
        socket = WebsocketManager.WebsocketDict[socket_name]
        socket.send(self.__prepare_unsubscribe_message__(symbol, interval))

    def _on_message_(self, message):
        pass

    def _on_error_(self, error):
        pass

    def _on_close_(self, close_status_code, close_msg):
        pass

    def _on_open_(self):
        pass

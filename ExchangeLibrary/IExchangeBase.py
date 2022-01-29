from enum import Enum, auto
import requests
import tqdm
from math import ceil
import threading
from queue import Queue
from candle import Candle, CandleKey, ValidIndicators
from abc import ABC, abstractmethod, abstractclassmethod


class ExchangeValidOrders(Enum):
    limit = auto()
    market = auto()
    stop_limit = auto()
    take_profit = auto()


class ExchangeValidEndpoints(Enum):
    GetAvailableCurrencies = auto()
    GetCandles = auto()
    WebsocketEndpoint = auto()


class ExchangeInterface(ABC):
    throttle_ms: int  # time gap between each request
    data: Candle

    def __init__(self) -> None:
        pass

    def get_available_coins(self, url):
        req = requests.get(url)
        return req.content
    @abstractmethod
    def get_candles(self, url: str, start_time: int, end_time: int, time_interval: int, body: str) -> None:
        curr = start_time
        total_num = ceil((end_time - start_time) / time_interval)
        progress_bar = tqdm.tqdm(total=total_num)
        queue = Queue()  # thread_safe queue

        while curr < end_time:
            progress_bar.update(1)
            req = body % (curr, curr + time_interval)
            t = threading.Thread(target=self.__make_request__, args=(url, req, queue))
            t.start()
            curr += time_interval

    def __make_request__(self, url: str, body: str, cq: Queue) -> None:
        req = requests.get(url, params=body).content
        cq.put(list(map(lambda x: list(map(float, x)), eval(req))))  # reorganized

    def save_candles(self):
        pass

    def read_candles(self):
        pass

    def connect_to_websocket(self):
        pass

    def close_connection(self):
        pass

    def limit_order(self):
        pass

    def market_order(self):
        pass

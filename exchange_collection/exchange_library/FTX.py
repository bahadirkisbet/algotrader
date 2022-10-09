from datetime import timedelta
from queue import Queue
from threading import Thread
from time import sleep

import requests

from exchange_collection.exchange_base import *


class FTX(ExchangeBase):
    """
        FTX is a cryptocurrency exchange.
        - https://ftx.com/
    """
    name: str = "FTX"
    websocket_url: str = "wss://ftx.com/ws/v2"
    api_url: str = "https://ftx.com/api"
    api_endpoints: dict = {
        "fetch_candle": "/markets/{symbol}/candles?granularity={granularity}&start={start}&end={end}",
        "fetch_product_list": "/markets"
    }

    def __init__(self, config: configparser.ConfigParser, logger: logging.Logger) -> None:
        super().__init__(config, logger)
        self.limit = 1000
        self.throttle_seconds = 0.2

    def fetch_product_list(self):
        pass

    def fetch_candle(self, symbol: str, start_date: datetime, end_date: datetime, interval: Interval) -> list:
        interval_in_seconds = self.interval_to_granularity(interval)
        url = self.api_url + self.api_endpoints["fetch_candle"]

        params = []

        while start_date <= end_date:
            start_time = int(start_date.timestamp())
            end_time = int((start_date + timedelta(seconds=interval_in_seconds * (self.limit - 1))).timestamp())

            params.append(
                url.format(
                    market_name=symbol,
                    resolution=interval_in_seconds,
                    start_time=start_time,
                    end_time=end_time)
            )
            start_date += timedelta(seconds=(interval_in_seconds * self.limit))

        queue: Queue = Queue()
        tasks = list()
        for param in params:
            task = Thread(target=self.__get_candle__, args=(param, queue))
            task.start()
            tasks.append(task)
            sleep(self.throttle_seconds)

        for task in tasks:
            task.join()

        result = list()
        while self.queue.empty() is False:
            data = self.queue.get()
            if data.get("success", False):  # if the request was successful, get the data
                result.extend(data.get("result", []))
        return result

    def __get_candle__(self, url: str, queue: Queue) -> list:
        try:
            response = requests.get(url)
            queue.put(response.json())
        except Exception as e:
            self.logger.exception(e)

    def interval_to_granularity(self, interval: Interval) -> int:
        match interval:
            case Interval.ONE_MINUTES:
                return 60
            case Interval.FIVE_MINUTES:
                return 300
            case Interval.FIFTEEN_MINUTES:
                return 900
            case Interval.ONE_HOUR:
                return 3600
            case Interval.ONE_DAY:
                return 86400
        return 0

    def subscribe_to_websocket(self, symbols: List[str], interval: Interval) -> None:
        socket_name = self._create_websocket_connection_(self.websocket_url)
        socket: websocket.WebSocketApp = self._websocket_dict_[socket_name]
        try:
            data = "test"
            socket.send(data)
        except Exception as exception:
            self.logger.exception(exception)

    def unsubscribe_from_websocket(self, symbol: str, interval: Interval) -> None:
        pass

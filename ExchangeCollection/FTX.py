from datetime import timedelta, datetime
from queue import Queue
from threading import Thread
from time import sleep
from regex import W

import requests
from ExchangeCollection.ExchangeBase import *
from concurrent.futures import ThreadPoolExecutor
import concurrent

class FTX(ExchangeBase):
    """
        FTX is a cryptocurrency exchange.
        - https://ftx.com/
    """

    name: str = "FTX"
    websocket_url: str = "wss://ftx.com/ws/v2"
    api_url: str = "https://ftx.com/api"

    def __init__(self):
        super().__init__()
        self.api_endpoints = {
            "fetch_candle": "/markets/{market_name}/candles?resolution={resolution}&start_time={start_time}&end_time={end_time}",
        }
        self.limit = 1000
        self.queue: Queue = Queue()

    def fetch_candle(self, symbol: str, startDate: datetime, endDate: datetime, interval: Interval) -> list:
        interval_in_seconds = self.interval_to_granularity(interval)
        url = self.api_url + self.api_endpoints["fetch_candle"]

        params = []
    
        while startDate <= endDate:
            params.append( 
                url.format( 
                    market_name=symbol, 
                    resolution=interval_in_seconds, 
                    start_time=int(startDate.timestamp()), 
                    end_time=int((startDate + timedelta(seconds=interval_in_seconds * (self.limit - 1))).timestamp())
                    )
                )
            startDate += timedelta(seconds=(interval_in_seconds * self.limit))
        tasks = list()
        for param in params:
            task = Thread(target=self.__get_candle__, args=(param, self.queue))
            task.start()
            tasks.append(task)
            sleep(0.1)

        for task in tasks:
            task.join()

        while self.queue.empty() is False:
            data = self.queue.get()
            print(data)

    def __get_candle__(self, url: str, queue: Queue) -> list:
        try:
            print("URL -> ", url)
            response = requests.get(url)
            queue.put(response.json())
        except Exception as e:
            print(e)

    def interval_to_granularity(self, interval: Interval) -> int:
        match interval:
            case Interval.ONE_MINUTES: return 60
            case Interval.FIVE_MINUTES: return 300
            case Interval.FIFTEEN_MINUTES: return 900
            case Interval.ONE_HOUR: return 3600
            case Interval.ONE_DAY: return 86400
        return 0


    def subscribe_to_websocket(self, symbol: str, interval: Interval) -> None:
        pass

    def unsubscribe_from_websocket(self, symbol: str, interval: Interval) -> None:
        pass
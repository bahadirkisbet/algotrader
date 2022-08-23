from datetime import timedelta, datetime
from queue import Queue
from threading import Thread
from time import sleep
import logging

import requests
from ExchangeCollection.ExchangeBase import *

class FTX(ExchangeBase):
    """
        FTX is a cryptocurrency exchange.
        - https://ftx.com/
    """

    name: str = "FTX"
    websocket_url: str = "wss://ftx.com/ws/v2"
    api_url: str = "https://ftx.com/api"
    api_endpoints: dict = {
        "fetch_candle": "/markets/{symbol}/candles?granularity={granularity}&start={start}&end={end}"
    }

    def __init__(self, config: configparser.ConfigParser, logger: logging.Logger) -> None:
        super().__init__(config, logger)
        self.limit = 1000
        self.throttle_seconds = 0.2
        

    def fetch_candle(self, symbol: str, startDate: datetime, endDate: datetime, interval: Interval) -> list:
        interval_in_seconds = self.interval_to_granularity(interval)
        url = self.api_url + self.api_endpoints["fetch_candle"]

        params = []
    
        while startDate <= endDate:
            startTime = int(startDate.timestamp())
            endTime = int((startDate + timedelta(seconds=interval_in_seconds * (self.limit - 1))).timestamp())

            params.append( 
                url.format( 
                    market_name=symbol, 
                    resolution=interval_in_seconds, 
                    start_time=startTime, 
                    end_time=endTime)
                )
            startDate += timedelta(seconds=(interval_in_seconds * self.limit))

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
            if data.get("success", False): # if the request was successful, get the data
                result.extend(data.get("result", []))
        

    def __get_candle__(self, url: str, queue: Queue) -> list:
        try:
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

import sys

import requests
import os
from tqdm import tqdm
from math import ceil
from utils import current_ms
from typing import Any
import json
import websocket
from configs import CONFIG
import threading

class Exchange:
    cfg: dict
    data: dict
    pipe: Any
    symbol: str
    sckt: websocket.WebSocket
    thread: threading.Thread

    def __init__(self, _symbol, _cfg, _pipe, _file_path=""):
        '''
        :param _cfg: config file for an exchange
        :param _pipe: a pipeline for the communication between other classes
        :param _file_path: if there is an archive in the file, read it
        '''
        self.symbol = _symbol
        self.cfg = _cfg
        self.pipe = _pipe
        self.sckt = websocket.WebSocket()
        if _file_path != "":  # there is a path given
            pass
            # self.read_data(_file_path)

    def get_available_coins(self):
        url = self.cfg["endpoints"]["api"] + self.cfg["endpoints"]["coins"]
        req = requests.get(url)
        return req.content

    def get_candles(self, symbol, interval, start_time, end_time=None):

        url = self.cfg["endpoints"]["api"] + self.cfg["endpoints"]["candles"]

        current_time = start_time
        last_time = end_time if end_time is not None else current_ms()

        result = list()
        time_gap = 300000 * 1000

        total_num = ceil((last_time - current_time) / time_gap)
        progress_bar = tqdm(total=total_num)  # visual and simple progress bar

        while current_time < last_time:
            progress_bar.update(1)  # everytime, it increases progress by one

            # The request body prepared by the user. The next line can be changed by the parameters
            body = eval(self.cfg["request_body"]["candle"] % (symbol, interval, current_time, current_time + time_gap))

            req = requests.get(url, params=body).content
            current_time += time_gap
            result.extend(list(map(lambda x: list(map(float, x)), eval(req))))

        return result

    def prepare_request_body(self, symbol, interval, start_time, end_time):
        if self.cfg["exchange_code"] == "BNB":
            return {
                "symbol": symbol,
                "interval": self.intervals[interval],  # mapping for the corresponding exchange
                "startTime": int(start_time),
                "endTime": int(end_time),
                "limit": "1000"
            }
        else:
            raise "Exchange Not Found!"

    def save_data(self, key, path):
        try:
            file_name = f"{self.cfg['exchange_code']}_{self.symbol}_{key}.json"
            with open(path + file_name, 'w') as out:
                json.dumps(self.data[key], out)

        except Exception as e:
            print(e)

    def read_data(self, key, path):
        try:
            with open(path, 'r') as in_file:
                self.data[key] = json.load(in_file)

        except Exception as e:
            print(e)

    def connect_to_websocket(self, interval):
        self.thread = threading.Thread(target=self.__socket_connection(interval))
        self.thread.start()

    def __socket_connection(self, interval):
        url = self.cfg["endpoints"]["websocket"]
        url += self.cfg["endpoints"]["websocket_extra"] % (self.symbol, interval)
        self.sckt.connect(url)
        if self.sckt.connected:
            print("Connection is successful")
        else:
            print("There is a problem in connection")

        # sub_ms = json.dumps({
        #     "method": "SUBSCRIBE",
        #     "params": ['btcusdt@kline_5m'],
        #     "id": 1
        # })
        sub_msg = self.cfg["request_body"]["subscribe"] % ('btcusdt', 'kline', interval)
        sub_msg = json.dumps(eval(sub_msg)) # Somehow, it gives an error if you convert it into dict and then string.

        self.sckt.send(sub_msg)

        while True:
            msg = json.loads(self.sckt.recv())
            print(msg)
        sys.exit()

class ExchangeHandler:
    endpoints: dict
    fields: list
    exchange_name: str
    intervals: dict
    data: dict
    symbol: str
    starts_from: int
    pipe: Any

    def __init__(self, exchange_name, symbol, starting_time, pipe, read_from_file=True):
        self.endpoints = dict()
        self.pipe = pipe
        if exchange_name == 'BNB':
            self.endpoints['api'] = "https://api.binance.com"
            self.endpoints['candles'] = "/api/v3/klines"
            self.endpoints['currencies'] = "/api/v3/exchangeInfo"
            self.endpoints["websocket"] = "wss://stream.binance.com:9443"
            self.fields = ["open_time",  # 0
                           "open",  # 1
                           "high",  # 2
                           "low",  # 3
                           "close",  # 4
                           "volume",  # 5
                           "close_time",  # 6
                           "quote_asset_volume",  # 7
                           "number_of_trades",  # 8
                           "taker_buy_asset_volume",  # 9
                           "taker_buy_quote_volume",  # 10
                           "nothing"]  # 11
            self.exchange_name = "BNB"
            self.intervals = {
                5: "5m",
                15: "15m",
                30: "30m",
                60: "1h",
                240: "4h",
                1440: "1d"
            }
        else:
            raise "Exchange Not Found!"

        self.symbol = symbol
        self.starts_from = starting_time
        self.data = dict()

        if read_from_file:
            if os.path.isfile(f"archive/{exchange_name}_{symbol}_5.json"):
                self.read_data([f"archive/{exchange_name}_{symbol}_5.json"])
                self.retrieve_missing_candles([5])
            else:
                print("File Not Found !!")
        else:
            self.data = {
                5: self.get_candles(symbol, 5, starting_time)  # 5 minutes candle data
            }

    def get_available_currencies(self):
        url = self.endpoints["api"] + self.endpoints["currencies"]
        req = requests.get(url)
        return req.content

    def get_candles(self, symbol, interval, start_time, end_time=None):

        url = self.endpoints["api"] + self.endpoints["candles"]

        current_time = start_time
        last_time = end_time if end_time is not None else current_ms()

        result = list()
        time_gap = 300000 * 1000

        total_num = ceil((last_time - current_time) / time_gap)
        progress_bar = tqdm(total=total_num)  # visual and simple progress bar

        while current_time < last_time:
            progress_bar.update(1)  # everytime, it increases progress by one

            body = self.prepare_request_body(symbol, interval, current_time, current_time + time_gap)
            req = requests.get(url, params=body).content
            current_time += time_gap
            result.extend(list(map(lambda x: list(map(float, x)), eval(req))))

        return result

    def prepare_request_body(self, symbol, interval, start_time, end_time):
        if self.exchange_name == "BNB":
            return {
                "symbol": symbol,
                "interval": self.intervals[interval],  # mapping for the corresponding exchange
                "startTime": int(start_time),
                "endTime": int(end_time),
                "limit": "1000"
            }
        else:
            raise "Exchange Not Found!"

    def aggregate_candles(self, intervals: list):
        for interval in intervals:
            if interval not in self.data:
                dividend_time_frame = self.get_biggest_smaller_time_frame(interval)
                group_size = interval // dividend_time_frame
                self.data[interval] = self.__aggregate_candles_handles(dividend_time_frame, group_size)

    def __aggregate_candles_handles(self, interval, number):
        if self.exchange_name == "BNB":
            return self.__aggregate_tool_bnb(self.data[interval], number)
        else:  # add other exchanges here
            raise "Error: Exchange not found in aggregation"

    def save_data(self, intervals, path="archive/"):
        for interval in intervals:
            file_name = f"{self.exchange_name}_{self.symbol}_{interval}.json"
            try:
                with open(path + file_name, 'w') as out:
                    json.dumps(self.data[interval])
            except Exception as err:
                print("Exception has occurred in 'save_data': ", err)

    def read_data(self, paths):
        for path in paths:
            file_name = path.split("/")[-1]
            exchange_name, symbol, interval = file_name.split("_")
            try:
                with open(path, 'r') as in_file:
                    self.data[int(interval)] = json.loads(in_file)
                self.symbol = symbol
                self.exchange_name = exchange_name
            except Exception as err:
                print("Exception has occurred in 'read_data': ", err)

    def retrieve_missing_candles(self, intervals):
        for interval in intervals:

            if len(self.data) and interval in self.data:  # if the key is in the dict
                self.data[interval].update(
                    self.get_candles(self.symbol,
                                     interval,
                                     self.data[interval][-1]["close_time"])
                )
            else:  # otherwise, add the key
                self.data[interval] = self.get_candles(self.symbol,
                                                       interval,
                                                       self.starts_from)

    # REGION: EXCHANGE SPECIFIC FUNCTIONS
    def __aggregate_tool_bnb(self, candles: dict, number):

        res = dict()
        for i in range(0, len(candles), number):
            temp = [0] * 12
            temp[0] = candles[i]["open_time"]
            temp[1] = candles[i]["open"]
            temp[2] = 0  # high
            temp[3] = 99999999  # low
            temp[4] = candles[min(i + number - 1, len(candles) - 1)]["close"]
            temp[5] = 0  # volume
            temp[6] = candles[min(i + number - 1, len(candles) - 1)]["close_time"]

            for j in range(min(number, candles.shape[0] - i)):
                temp[2] = max(candles.iloc[i + j]["high"], temp[2])
                temp[3] = min(candles.iloc[i + j]["low"], temp[3])
                temp[5] += candles.iloc[i + j]["volume"]
                temp[7] += candles.iloc[i + j]["quote_asset_volume"]
                temp[8] += candles.iloc[i + j]["number_of_trades"]
                temp[9] += candles.iloc[i + j]["taker_buy_asset_volume"]
                temp[10] += candles.iloc[i + j]["taker_buy_quote_volume"]
            res.update(temp)
        return res

    # END REGION: EXCHANGE SPECIFIC FUNCTIONS

    # REGION: HELPERS
    def get_biggest_smaller_time_frame(self, time_frame):
        """
        :param time_frame: given time interval
        :return: it returns the biggest time frame that is smaller than the parameter "time_frame"
        """

        keys = sorted(self.data.keys())
        keys.reverse()
        ind = keys.index(time_frame)
        return ind + 1 if ind + 1 != len(keys) else ind
    # END REGION: HELPERS


if __name__ == "__main__":
    exchange = Exchange("BTCUSDT", CONFIG["BNB_spot"], "")
    exchange.connect_to_websocket("5m")

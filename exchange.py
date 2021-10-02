import pandas as pd
import requests
import os
from tqdm import tqdm
from math import ceil
from utils import current_ms


class ExchangeHandler:
    endpoints: dict
    fields: list
    exchange_name: str
    intervals: dict
    data: dict
    symbol: str
    starts_from: int

    def __init__(self, exchange_name, symbol, starting_time):
        self.endpoints = dict()

        if exchange_name == 'BNB':
            self.endpoints['api'] = "https://api.binance.com"
            self.endpoints['candles'] = "/api/v3/klines"
            self.endpoints['currencies'] = "/api/v3/exchangeInfo"
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

        if os.path.isfile(f"archive/{exchange_name}_{symbol}_5"):
            self.read_data([f"archive/{exchange_name}_{symbol}_5"])
            self.retrieve_missing_candles([5])
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
        last_time = end_time if end_time != None else current_ms()

        result = list()
        time_gap = 300000 * 1000

        total_num = ceil((last_time - current_time) / time_gap)
        progress_bar = tqdm(total=total_num)  # visual and simple progress bar

        while current_time < last_time:
            progress_bar.update(1)  # everytime, it increases progress by one

            body = self.prepare_request_body(symbol, interval, current_time, current_time + time_gap)
            req = requests.get(url, params=body).content
            current_time += time_gap
            result.extend(list(map(lambda x: list(map(lambda y: float(y), x)), eval(req))))

        return pd.DataFrame(data=result, columns=self.fields)

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
            file_name = f"{self.exchange_name}_{self.symbol}_{interval}"
            try:
                self.data[interval].to_pickle(path + file_name)
            except Exception as err:
                print("Exception has occurred: ", err)
        return True

    def read_data(self, paths):
        for path in paths:
            file_name = path.split("/")[-1]
            exchange_name, symbol, interval = file_name.split("_")
            try:
                self.data[int(interval)] = pd.read_pickle(path)
                self.symbol = symbol
                self.exchange_name = exchange_name
            except Exception as err:
                print("Exception has occurred: ", err)

    def retrieve_missing_candles(self, intervals):
        for interval in intervals:
            temp = self.get_candles(self.symbol,
                                    interval,
                                    self.data[interval].iloc[-1]["close_time"])
            self.data[interval] = pd.concat(
                [self.data[interval], temp],
                ignore_index=True
            )

    # REGION: EXCHANGE SPECIFIC FUNCTIONS
    def __aggregate_tool_bnb(self, candles: pd.DataFrame, number):

        res = pd.DataFrame(columns=self.columns)
        for i in range(0, candles.shape[0], number):
            temp = [0] * 12
            temp[0] = candles.iloc[i]["open_time"]
            temp[1] = candles.iloc[i]["open"]
            temp[2] = 0  # high
            temp[3] = 99999999  # low
            temp[4] = candles.iloc[min(i + number - 1, candles.shape[0] - 1)]["close"]
            temp[5] = 0  # volume
            temp[6] = candles.iloc[min(i + number - 1, candles.shape[0] - 1)]["close_time"]

            for j in range(min(number, candles.shape[0] - i)):
                temp[2] = max(candles.iloc[i + j]["high"], temp[2])
                temp[3] = min(candles.iloc[i + j]["low"], temp[3])
                temp[5] += candles.iloc[i + j]["volume"]
                temp[7] += candles.iloc[i + j]["quote_asset_volume"]
                temp[8] += candles.iloc[i + j]["number_of_trades"]
                temp[9] += candles.iloc[i + j]["taker_buy_asset_volume"]
                temp[10] += candles.iloc[i + j]["taker_buy_quote_volume"]
            res = res.append({
                "open_time": temp[0],
                "open": temp[1],
                "high": temp[2],
                "low": temp[3],
                "close": temp[4],
                "volume": temp[5],
                "close_time": temp[6],
                "quote_asset_volume": temp[7],
                "number_of_trades": temp[8],
                "taker_buy_asset_volume": temp[9],
                "taker_buy_quote_volume": temp[10],
                "nothing": temp[11]
            }, ignore_index=True)
        return res

    # END REGION: EXCHANGE SPECIFIC FUNCTIONS

    # REGION: HELPERS
    def get_biggest_smaller_time_frame(self, time_frame):
        keys = sorted(self.data.keys())
        keys.reverse()
        ind = keys.index(time_frame)
        return ind + 1 if ind + 1 != len(keys) else ind
    # END REGION: HELPERS


if __name__ == "__main__":
    beginning_time = 1500238800000
    exchange = ExchangeHandler("BNB", "BTCUSDT", beginning_time)
    exchange.save_data([5])

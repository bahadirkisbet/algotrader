import pandas as pd
import requests
import time
import os
from tqdm import tqdm
from math import ceil


def current_ms():
    return round(time.time() * 1000)


class ExchangeService:
    service_url: str
    columns: list

    def __init__(self):

        self.service_url = "https://api.binance.com"
        self.columns = ["open_time", "open", "high", "low", "close", "volume", "close_time",
                        "quote_asset_volume", "number_of_trades", "taker_buy_asset_volume", "taker_buy_quote_volume",
                        "nothing"]

    def get_available_currencies(self):

        url = self.service_url + "/api/v3/exchangeInfo"
        req = requests.get(url)
        return req.content

    def get_5minuteCandles(self, _symbol, _startTime):

        url = self.service_url + "/api/v3/klines" # corresponding endpoint

        endtime = current_ms()
        currtime = _startTime

        res = list()
        time_gap = 300000 * 1000

        total_num = ceil((endtime - currtime) / time_gap)
        progress_bar = tqdm(total=total_num)  # visual and simple progress bar
        while currtime < endtime:
            progress_bar.update(1)  # everytime, it increases progress by one
            body = {
                "symbol": _symbol,
                "interval": "5m",
                "startTime": currtime,
                "endTime": currtime + time_gap,  # ms value for 5 minutes
                "limit": "1000"
            }
            currtime += time_gap
            res.extend(list(map(lambda x: list(map(lambda y: float(y), x)), eval(
                requests.get(url, params=body).content))))
        return res

    def aggregate_candles(self, _symbol, _startTime):

        candles = self.get_5minuteCandles(_symbol, _startTime)

        data = dict()
        data["5m"] = pd.DataFrame(data=candles, columns=self.columns)
        data["15m"] = self.aggregate_tool(data["5m"], 3)
        data["30m"] = self.aggregate_tool(data["15m"], 2)
        data["1h"] = self.aggregate_tool(data["30m"], 2)
        data["4h"] = self.aggregate_tool(data["1h"], 4)

        return data

    def aggregate_tool(self, candles: pd.DataFrame, number):

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

    def save_candles(self, _path, _candles: pd.DataFrame, archive_folder_name="archive"):
        """
        :param archive_folder_name: archive folder name
        :param _path: this is relative path starting from archive folder
        :param _candles: the candle data in the form of  Pandas DataFrame
        :return: True if successful otherwise False
        """

        try:
            if os.path.isdir(archive_folder_name):
                _candles.to_pickle(_path)
                return True
            else:
                print("Corresponding archive folder is not found.")
                return False
        except:
            print("There is a problem occurred in saving candles")
            return False

    def read_candles(self, _path, archive_folder_name="archive"):
        """
        :param archive_folder_name: archive folder name
        :param _path: this is relative path starting from archive folder
        :return: candles if successful otherwise None
        """

        try:
            if os.path.isdir(archive_folder_name):
                return pd.read_pickle(_path)
            else:
                print("Corresponding archive folder is not found.")
                return None
        except:
            print("There is a problem occurred in saving candles")
            return None

    def retrieve_missing_candles(self, _path, archive_folder_name="archive"):
        """
        :param archive_folder_name: archive folder name
        :param _path: this is relative path starting from archive folder
        :return: candles if successful otherwise None
        """
        try:
            if os.path.isdir(archive_folder_name):
                candles: pd.DataFrame = pd.read_pickle(_path)
                symbol_name = _path.split("/")[-1].split("_")[1]
                remaining_candles = self.get_5minuteCandles(symbol_name, candles.iloc[-1]["close_time"])
                candles = pd.concat([candles, remaining_candles])
                return candles

            else:
                print("Corresponding archive folder is not found.")
                return None
        except:
            print("There is a problem occurred in saving candles")
            return None



if __name__ == "__main__":

    exchange = ExchangeService()
    beginning_time = 1500238800000

    exchange.save_candles("BNB_BTCUSDT_5m",
                          exchange.get_5minuteCandles("BTCUSDT",beginning_time))

import json

import pandas as pd
from enum import Enum
import gzip

class CandleKey(Enum):
    ts = 0  # timestamp
    o = 1  # open
    h = 2  # high
    l = 3  # low
    c = 4  # close
    v = 5  # volume


class ValidIndicators(Enum):
    SimpleMovingAverage = "SMA"
    ExponentialMovingAverage = "EMA"


class Candle:

    # static methods
    @staticmethod
    def __check_is_valid_indicators__(indicator_list: list) -> list:
        if indicator_list is None:
            return []
        for indicator in indicator_list:
            if not isinstance(indicator, ValidIndicators):
                raise ValueError("Invalid indicator type")
        return indicator_list

    # public methods
    def add_data(self, df: pd.DataFrame):
        pass

    def add_ival(self, df: pd.DataFrame):
        pass

    def get_ival(self, l: [ValidIndicators]):
        pass

    def get_symbol(self):
        return self.__symbol__

    def save_data(self, file_name: str, gzipped: bool = True) -> None:
        content = {
            "symbol": self.__symbol__,
            "indicator_list": self.__indicator_list__,
            "data": self.data,
            "indicator_values": self.indicator_values
        }
        content = json.dumps(content)

        if gzipped:
            with gzip.open(file_name, 'wb') as f:
                f.write(content)
        else:
            with open(file_name, 'w') as f:
                f.write(content)

    def read_data(self, file_name: str, gzipped: bool = True) -> None:
        if gzipped:
            with gzip.open(file_name, 'rb') as f:
                content = f.read()
        else:
            with open(file_name, 'r') as f:
                content = f.read()
        content = json.loads(content)

        self.__symbol__ = content["symbol"]
        self.__indicator_list__ = content["indicator_list"]
        self.__data__ = content["data"]
        self.__indicator_values__ = content["indicator_values"]

    def update(self):
        # update candle and calculate all possible 
        pass

    # private methods

    def __init__(self, symbol=None, indicator_list=None):
        self.__data__ = dict()
        self.__symbol__ = symbol
        self.__indicator_values__ = dict()  # the corresponding values of the indicators
        self.__indicator_list__ = self.__check_is_valid_indicators__(indicator_list)  # list of indicator instances

    def __index__(self):
        return self.__data__.index

    def __len__(self):
        return len(self.__data__)

    def __calculate_indicators__(self):
        pass


if __name__ == "__main__":
    pass

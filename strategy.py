from typing import Any
import pandas as pd


class Strategy:
    trade_open: bool
    candles: pd.DataFrame
    strategy: Any
    values: dict

    def __init__(self, _indicator_list, _candles):
        self.candles = _candles
        self.trade_open = False

    def buy(self):  # Virtual
        pass

    def sell(self):  # Virtual
        pass

    def update(self):  # Virtual

        self.candles.a
        # Calculate the indicators

        # Determine buy or sell
        pass

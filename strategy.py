from typing import Any
from exchange import ExchangeHandler
import pandas as pd


class Strategy:
    trade_open: bool
    candles: pd.DataFrame
    strategy: Any
    values: dict
    exchange: ExchangeHandler
    symbol: str

    def __init__(self, _indicator_list, _exchange_code, _symbol, _date):
        self.trade_open = False
        self.exchange = ExchangeHandler(_exchange_code, _symbol, _date)

    def buy(self):  # Virtual
        pass

    def sell(self):  # Virtual
        pass

    def update(self):  # Virtual

        self.candles.a
        # Calculate the indicators

        # Determine buy or sell
        pass

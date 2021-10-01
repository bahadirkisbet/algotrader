from exchange import *
from strategy import Strategy

COINS = {
    "BTCUSDT",
    "ETHUSDT",
    "XRPUSDT"
}


class BackTest:
    candles: pd.DataFrame
    strategies: Strategy

    def __init__(self, _candles, _strategies):
        self.candles = _candles
        self.strategies = _strategies

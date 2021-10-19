from exchange import *
from strategy import Strategy


class BackTest:
    candles: pd.DataFrame
    strategies: Strategy
    stats: dict

    def __init__(self, _candles, _strategy, _balance):
        self.candles = _candles
        self.strategy = _strategy
        self.stats = {
            "won": 0,
            "lost": 0,
            "neutral": 0,  # when the candle touches both stop-loss and take-profit point
            "balance": _balance,
            "profit": 0
        }

    def start(self):

        for _ in range(self.candles.shape[0]): # every candles goes in to the back test world one by one
            pass
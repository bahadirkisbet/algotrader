import ta
import pandas as pd

VALID_INDICATORS = {
    "MA"
}

class Strategy:
    trade_open: bool

    def __init__(self, _candles, _indicator_list):
        self.trade_open = False

    def buy(self):
        pass
    
    def sell(self):
        pass

    def update(self):
        pass
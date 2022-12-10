

class Candle:
    """
        A class to represent a candlestick.
    """
    def __init__(self,
                 timestamp: int,
                 open: float,
                 high: float,
                 low: float,
                 close: float,
                 volume: float,
                 trade_count: int):
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.timestamp = timestamp
        self.trade_count = trade_count


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
        self.timestamp = timestamp
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.trade_count = trade_count

    def __str__(self):
        return f"{self.timestamp} - " \
               f"{self.open} - " \
               f"{self.high} - " \
               f"{self.low} - " \
               f"{self.close} - " \
               f"{self.volume} - " \
               f"{self.trade_count}"

    def get_json(self):
        return vars(self)


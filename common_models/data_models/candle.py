
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

    def __str__(self):
        return f"{self.timestamp} - " \
               f"{self.open} - " \
               f"{self.high} - " \
               f"{self.low} - " \
               f"{self.close} - " \
               f"{self.volume} - " \
               f"{self.trade_count}"

    def get_readable(self):
        return f"""
            Timestamp: {self.timestamp}
            Open: {self.open}
            High: {self.high}
            Low: {self.low}
            Close: {self.close}
            Volume: {self.volume}
            Trade Count: {self.trade_count}
        """

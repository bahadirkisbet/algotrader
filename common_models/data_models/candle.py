

class Candle:
    """
        A class to represent a candlestick.
    """

    def __init__(self,
                 symbol: str,
                 timestamp: int,
                 open: float,
                 high: float,
                 low: float,
                 close: float,
                 volume: float,
                 trade_count: int):
        self.symbol = symbol
        self.timestamp = timestamp
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.trade_count = trade_count

    @staticmethod
    def read_json(json_data: dict):
        return Candle(
            symbol=json_data["symbol"],
            timestamp=json_data["timestamp"],
            open=json_data["open"],
            high=json_data["high"],
            low=json_data["low"],
            close=json_data["close"],
            volume=json_data["volume"],
            trade_count=json_data["trade_count"]
        )

    def __str__(self):
        return f"{self.symbol} - " \
               f"{self.timestamp} - " \
               f"{self.open} - " \
               f"{self.high} - " \
               f"{self.low} - " \
               f"{self.close} - " \
               f"{self.volume} - " \
               f"{self.trade_count}"

    def get_json(self) -> dict:
        return vars(self)

    @staticmethod
    def get_fields():
        return ["symbol", "timestamp", "open", "high", "low", "close", "volume", "trade_count"]

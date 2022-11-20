from enum import Enum, auto


class Interval(Enum):
    """
        Interval of the candle data.
        - Example: Let's say exchange says that give me the intervals in seconds,
            - "1m" -> 60
            - "5m" -> 300
            - "1h" -> 3600
            - "1d" -> 86400
    """
    ONE_MINUTES = auto()
    FIVE_MINUTES = auto()
    FIFTEEN_MINUTES = auto()
    THIRTY_MINUTES = auto()
    ONE_HOUR = auto()
    ONE_DAY = auto()

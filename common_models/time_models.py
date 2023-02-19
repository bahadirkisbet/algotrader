from enum import IntEnum


class Interval(IntEnum):
    """
        Interval of the candle data.
        - Example: Let's say exchange says that give me the intervals in seconds,
            - "1m" -> 60
            - "5m" -> 300
            - "1h" -> 3600
            - "1d" -> 86400
    """
    ONE_MINUTE = 1
    FIVE_MINUTES = 5
    FIFTEEN_MINUTES = 15
    THIRTY_MINUTES = 30
    ONE_HOUR = 60
    ONE_DAY = 1440


if __name__ == "__main__":
    print(Interval.FIVE_MINUTES.value)

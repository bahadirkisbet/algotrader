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
    FOUR_HOURS = 240
    ONE_DAY = 1440


def interval_to_frame(interval: Interval) -> str:
    """Convert interval to frame string for file naming."""
    return {
        Interval.ONE_MINUTE: "1m",
        Interval.FIVE_MINUTES: "5m",
        Interval.FIFTEEN_MINUTES: "15m",
        Interval.ONE_HOUR: "1h",
        Interval.ONE_DAY: "1d",
    }.get(interval, "1m")


def frame_to_interval(frame: str) -> Interval:
    """Convert frame string to interval enum."""
    return {
        "1m": Interval.ONE_MINUTE,
        "5m": Interval.FIVE_MINUTES,
        "15m": Interval.FIFTEEN_MINUTES,
        "1h": Interval.ONE_HOUR,
        "1d": Interval.ONE_DAY,
    }.get(frame, Interval.ONE_MINUTE)


if __name__ == "__main__":
    print(Interval.FIVE_MINUTES.value)
    print(interval_to_frame(Interval.FIVE_MINUTES))
    print(frame_to_interval("5m"))

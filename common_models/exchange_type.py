from enum import Enum, auto


class ExchangeType(Enum):
    """
        Exchange type.
    """
    SPOT = auto()
    FUTURES = auto()

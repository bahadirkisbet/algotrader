from enum import Enum, auto


class StrategyResponse(Enum):
    """
        Strategy response options.
    """
    BUY = auto()
    SELL = auto()
    HOLD = auto()

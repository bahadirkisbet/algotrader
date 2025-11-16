from enum import Enum, auto


class PositionType(Enum):
    LONG = auto()
    SHORT = auto()
    HOLD = auto()
    NONE = auto()

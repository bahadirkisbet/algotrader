from datetime import datetime

from modules.trading.account.position_type import PositionType


class StrategyResponse:
    """
    Strategy response class for handling the strategy response.
    """

    def __init__(
        self, position_type: PositionType, price: float, quantity: float, timestamp: datetime
    ):
        self.position_type = position_type
        self.quantity = quantity
        self.price = price
        self.timestamp = timestamp

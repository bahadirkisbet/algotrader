from datetime import datetime


class Position:
    """
    Position class for tracking the current position.
    """

    def __init__(self, symbol: str, quantity: float, entry_price: float, entry_time: datetime):
        self.symbol = symbol
        self.quantity = quantity
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.exit_price = None
        self.exit_time = None
        self.profit = None
        self.profit_percentage = None

        self.metadata = {}

    def close(self, exit_price: float, exit_time: datetime):
        """
        Close the position.
        """
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.status = "closed"
        self.profit = exit_price - self.entry_price
        self.profit_percentage = (self.profit / self.entry_price) * 100

    def update_price(self, new_price: float):
        """
        Update the price of the position.
        """
        self.current_price = new_price

    def get_profit(self):
        """
        Get the profit of the position.
        """
        return self.profit

    def get_profit_percentage(self):
        """
        Get the profit percentage of the position.
        """
        return self.profit_percentage

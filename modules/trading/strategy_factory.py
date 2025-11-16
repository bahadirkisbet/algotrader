from modules.trading.strategy.parabolic_sar_strategy import ParabolicSARStrategy
from modules.trading.strategy.strategy import Strategy


class StrategyFactory:
    """
    Factory class for creating strategy instances.
    """

    @staticmethod
    def create_strategy(strategy_type: str) -> Strategy:
        """
        Create a strategy instance.
        """
        if strategy_type == "PARABOLIC_SAR":
            return ParabolicSARStrategy()

        raise ValueError(f"Invalid strategy type: {strategy_type}")

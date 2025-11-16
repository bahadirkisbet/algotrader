from modules.config.config_manager import ConfigManager
from modules.data_center import DataCenter
from modules.log import LogManager
from modules.trading.account.position_type import PositionType
from modules.trading.strategy.strategy_response import StrategyResponse
from modules.trading.strategy_factory import StrategyFactory


class TradingEngine:
    """
    Trading engine for executing trades.
    """

    def __init__(self, data_center: DataCenter):
        from modules.config.config_manager import get_config
        self.config = get_config()
        self.logger = LogManager.get_logger()
        self.dc = data_center
        self.strategy = StrategyFactory.create_strategy(self.config.trading.strategy_type)
        self.current_position_type = PositionType.NONE

    def run(self):
        """
        Run the trading engine.
        """
        strategy_response = self.strategy.execute(self.dc)

        self.handle_strategy_response(strategy_response)

    def stop(self):
        """
        Stop the trading engine.
        """
        if self.strategy and hasattr(self.strategy, "stop"):
            self.strategy.stop()

    def handle_strategy_response(self, strategy_response: StrategyResponse):
        """
        Handle the strategy response.
        """
        if strategy_response.position_type == PositionType.LONG:
            self.current_position_type = PositionType.LONG
        elif strategy_response.position_type == PositionType.SHORT:
            self.current_position_type = PositionType.SHORT
        elif strategy_response.position_type == PositionType.HOLD:
            self.current_position_type = PositionType.HOLD
        else:
            self.current_position_type = PositionType.NONE

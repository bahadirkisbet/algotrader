"""
Strategy class for executing trades.
"""

from datetime import datetime

from models.data_models.candle import Candle
from modules.config.config_manager import ConfigManager
from modules.data_center import DataCenter
from modules.log import LogManager
from modules.trading.account.position_type import PositionType
from modules.trading.strategy.strategy_response import StrategyResponse


class Strategy:
    """Strategy class for executing trades."""

    def __init__(self):
        from modules.config.config_manager import get_config
        self.config = get_config()
        self.logger = LogManager.get_logger()

    def execute(self, data_center: DataCenter) -> StrategyResponse:
        """Execute the strategy."""
        raise NotImplementedError("Subclasses must implement this method")

    def _create_long_response(self, candle: Candle) -> StrategyResponse:
        """Create a LONG position response."""
        # Calculate quantity based on some strategy (simplified)
        quantity = 100.0  # TODO: Calculate based on capital and risk management

        return StrategyResponse(
            position_type=PositionType.LONG,
            price=candle.close if candle else 0.0,
            quantity=quantity,
            timestamp=datetime.fromtimestamp(candle.timestamp / 1000) if candle else datetime.now(),
        )

    def _create_short_response(self, candle: Candle) -> StrategyResponse:
        """Create a SHORT position response."""
        # Calculate quantity based on some strategy (simplified)
        quantity = 100.0  # TODO: Calculate based on capital and risk management

        return StrategyResponse(
            position_type=PositionType.SHORT,
            price=candle.close if candle else 0.0,
            quantity=quantity,
            timestamp=datetime.fromtimestamp(candle.timestamp / 1000) if candle else datetime.now(),
        )

    def _create_hold_response(self, candle: Candle) -> StrategyResponse:
        """Create a HOLD response."""
        return StrategyResponse(
            position_type=PositionType.HOLD,
            price=candle.close if candle else 0.0,
            quantity=0.0,
            timestamp=datetime.fromtimestamp(candle.timestamp / 1000) if candle else datetime.now(),
        )

    def _create_none_response(self, candle: Candle) -> StrategyResponse:
        """Create a NONE response."""
        return StrategyResponse(
            position_type=PositionType.NONE,
            price=candle.close if candle else 0.0,
            quantity=0.0,
            timestamp=datetime.fromtimestamp(candle.timestamp / 1000) if candle else datetime.now(),
        )

    def stop(self):
        """Stop the strategy. Override in subclasses if needed."""
        pass

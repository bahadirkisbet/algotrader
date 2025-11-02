"""
Base classes for technical indicators.

This module provides base classes for technical indicators that use IndicatorManager
to fetch historical data instead of maintaining state.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional

from modules.config.config_manager import ConfigManager
from modules.data.candle import Candle
from modules.log import LogManager

if TYPE_CHECKING:
    from modules.indicators.indicator_manager import IndicatorManager


class BaseIndicator(ABC):
    """Abstract base class for all technical indicators."""

    def __init__(self):
        self.logger = LogManager.get_logger(ConfigManager.get_config())


class Indicator(BaseIndicator):
    """
    Base class for indicators that use IndicatorManager to fetch historical data.

    Indicators receive all necessary data through IndicatorManager,
    avoiding internal state management.
    """

    def __init__(self, symbol: str, indicator_manager: "IndicatorManager"):  # type: ignore
        """
        Initialize indicator.

        Args:
            symbol: Trading pair symbol
            indicator_manager: IndicatorManager instance for data retrieval
        """
        super().__init__()
        self.symbol = symbol
        self.indicator_manager = indicator_manager
        self.data: List[List[float]] = []  # [[timestamp, value], ...]
        self.code: str = "NotSet"

    def register(self) -> None:
        """Register this indicator instance with IndicatorManager."""
        self.indicator_manager.register_indicator(self.symbol, self.code, self)

    def get_previous_indicator_value(
        self, indicator_code: str, index: int = 0, reverse: bool = False
    ) -> Optional[float]:
        """
        Get a previous value from another indicator (or self).

        Args:
            indicator_code: Indicator code (e.g., "ema_9")
            index: Index offset
            reverse: If True, index from oldest; if False, index from newest

        Returns:
            Previous indicator value or None
        """
        return self.indicator_manager.get_indicator_value(
            self.symbol, indicator_code, index, reverse
        )

    @abstractmethod
    def calculate(self, candle: Candle, index: Optional[int] = None) -> Optional[float]:
        """
        Calculate indicator value for a single candle.

        Args:
            candle: Current candle to calculate for
            index: Optional index of current candle (used with request_callback)

        Returns:
            Calculated indicator value or None if insufficient data
        """

    def get(self, index: int = 0, reverse: bool = False) -> Optional[float]:
        """Get indicator value by index."""
        if not self.data:
            return None
        idx = len(self.data) - 1 - index if reverse else index
        if idx < 0 or idx >= len(self.data):
            return None
        return self.data[idx][1]

    def print(self, index: int = 0, reverse: bool = True) -> None:
        """Print indicator value."""
        value = self.get(index, reverse)
        if value is not None:
            self.logger.info("%s %s: %.8f", self.symbol, self.__class__.__name__, value)

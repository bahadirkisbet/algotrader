"""
Indicator Manager for managing and coordinating technical indicators.
"""

from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from modules.data.candle import Candle
from modules.indicator.indicator_factory import IndicatorFactory
from modules.log import LogManager

if TYPE_CHECKING:
    from modules.indicators.base import Indicator


class IndicatorManager:
    """
    Central manager for technical indicators.

    Manages indicator registration, retrieval, and provides callbacks for indicators
    to request historical candle data and previous indicator values.
    """

    def __init__(self, candle_request_callback: Callable[[str, int, bool], Optional[Candle]]):
        """
        Initialize IndicatorManager.

        Args:
            candle_request_callback: Callback to request historical candles
                Signature: (symbol: str, index: int, reverse: bool) -> Optional[Candle]
        """
        self.logger = LogManager.get_logger()
        self.candle_request_callback = candle_request_callback

        # Registry: {symbol: {indicator_code: indicator_instance}}
        self._indicator_registry: Dict[str, Dict[str, object]] = {}

    def register_indicator(self, symbol: str, indicator_code: str, indicator: object) -> None:
        """
        Register an indicator instance.

        Args:
            symbol: Trading pair symbol
            indicator_code: Unique code for the indicator (e.g., "ema_9")
            indicator: Indicator instance to register
        """
        if symbol not in self._indicator_registry:
            self._indicator_registry[symbol] = {}

        self._indicator_registry[symbol][indicator_code] = indicator
        self.logger.debug("Registered indicator %s for symbol %s", indicator_code, symbol)

    def get_indicator(self, symbol: str, indicator_code: str) -> Optional[object]:
        """
        Get an indicator instance by symbol and code.

        Args:
            symbol: Trading pair symbol
            indicator_code: Indicator code

        Returns:
            Indicator instance or None if not found
        """
        if symbol not in self._indicator_registry:
            return None
        return self._indicator_registry[symbol].get(indicator_code)

    def get_indicator_value(
        self, symbol: str, indicator_code: str, index: int = 0, reverse: bool = False
    ) -> Optional[float]:
        """
        Get a previous indicator value.

        This allows indicators like EMA to fetch their previous values
        instead of recalculating from scratch.

        Args:
            symbol: Trading pair symbol
            indicator_code: Indicator code (e.g., "ema_9")
            index: Index offset (0 = most recent)
            reverse: If True, index from oldest; if False, index from newest

        Returns:
            Indicator value or None if not found or out of bounds
        """
        indicator = self.get_indicator(symbol, indicator_code)
        if indicator is None:
            return None

        # Check if indicator has get method
        if not hasattr(indicator, "get"):
            return None

        return indicator.get(index, reverse)

    def request_candle(
        self, symbol: str, index: int = 0, reverse: bool = False
    ) -> Optional[Candle]:
        """
        Request a historical candle.

        Delegates to the candle_request_callback provided during initialization.

        Args:
            symbol: Trading pair symbol
            index: Index offset
            reverse: If True, index from oldest; if False, index from newest

        Returns:
            Candle or None if not found
        """
        return self.candle_request_callback(symbol, index, reverse)

    def get_all_indicators_for_symbol(self, symbol: str) -> Dict[str, object]:
        """
        Get all indicators registered for a symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            Dictionary of indicator_code -> indicator_instance
        """
        return self._indicator_registry.get(symbol, {})

    def clear_symbol(self, symbol: str) -> None:
        """
        Clear all indicators for a symbol.

        Args:
            symbol: Trading pair symbol
        """
        if symbol in self._indicator_registry:
            del self._indicator_registry[symbol]
            self.logger.debug("Cleared all indicators for symbol %s", symbol)

    def clear_all(self) -> None:
        """Clear all registered indicators."""
        self._indicator_registry.clear()
        self.logger.debug("Cleared all indicators")

    def create_indicator(self, indicator_type: str, symbol: str, **kwargs: Any) -> "Indicator":  # type: ignore
        """
        Create and register an indicator using IndicatorFactory.

        Args:
            indicator_type: Indicator type identifier (e.g., "SMA", "EMA", "ParabolicSAR")
            symbol: Trading pair symbol
            **kwargs: Additional parameters for the specific indicator

        Returns:
            Created Indicator instance (already registered)
        """

        indicator = IndicatorFactory.create_indicator(indicator_type, symbol, self, **kwargs)
        # Indicator is already registered in its __init__, so we just return it
        self.logger.debug("Created and registered %s for symbol %s", indicator_type, symbol)
        return indicator

    def create_indicators_for_symbol(
        self, symbol: str, indicator_configs: List[Dict[str, Any]]
    ) -> List["Indicator"]:  # type: ignore
        """
        Create multiple indicators for a symbol based on configuration.

        Args:
            symbol: Trading pair symbol
            indicator_configs: List of indicator configurations, each containing:
                - type: Indicator type identifier
                - **kwargs: Additional parameters for the indicator

        Returns:
            List of created Indicator instances

        Example:
            configs = [
                {"type": "SMA", "period": 20},
                {"type": "EMA", "period": 9},
                {"type": "ParabolicSAR", "acceleration": 0.02, "maximum": 0.20},
            ]
            indicators = manager.create_indicators_for_symbol("BTCUSDT", configs)
        """
        indicators = []
        for config in indicator_configs:
            indicator_type = config.pop("type")
            indicator = self.create_indicator(indicator_type, symbol, **config)
            indicators.append(indicator)

        self.logger.info("Created %d indicators for symbol %s", len(indicators), symbol)
        return indicators

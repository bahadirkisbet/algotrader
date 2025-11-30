"""
Indicator Manager for managing and coordinating technical indicators.
"""

from typing import Callable, Dict, List, Optional

from modules.indicator.base import Indicator
from modules.indicator.indicator_factory import IndicatorFactory
from modules.log import LogManager
from modules.model.candle import Candle


class IndicatorManager:
    """
    Central manager for technical indicators.

    Manages indicator registration, retrieval, and provides callbacks for indicators
    to request historical candle data and previous indicator values.
    """

    def __init__(
        self,
        candle_request_callback: Callable[[str, int, bool], Optional[Candle]],
        indicators: List[object],
    ):
        """
        Initialize IndicatorManager.

        Args:
            candle_request_callback: Callback to request historical candles
                Signature: (symbol: str, index: int, reverse: bool) -> Optional[Candle]
        """
        self.logger = LogManager.get_logger()
        self.candle_request_callback = candle_request_callback

        # indicator name, indicator instance
        self._indicator_instances: Dict[str, Indicator] = (
            self._create_indicators_from_config(indicators)
        )

    def _create_indicators_from_config(
        self, indicators: List[object]
    ) -> Dict[str, Indicator]:
        indicator_instances = {}
        for indicator_config in indicators:
            indicator = IndicatorFactory.create_indicator(
                indicator_config.get("code"),
                self,
                **indicator_config.get("parameters", {}),
            )
            indicator_instances[indicator.code] = indicator
        return indicator_instances

    def calculate(self, candle: Candle) -> None:
        """Calculate all indicators for a given candle.

        Args:
            candle (Candle): The candle to calculate the indicators for
        """
        for indicator in self._indicator_instances.values():
            value = indicator.calculate(candle)
            key = indicator.code
            candle.update(key, value)

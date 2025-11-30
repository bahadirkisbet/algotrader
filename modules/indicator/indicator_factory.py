"""
Indicator Factory for creating indicator instances.

This module provides a factory for creating technical indicator instances,
following the Factory design pattern and SOLID principles.
"""

from typing import Any, Dict, Type

from modules.indicator.base import Indicator
from modules.indicator.ema import EMA
from modules.indicator.indicator_manager import IndicatorManager
from modules.indicator.parabolic_sar import ParabolicSAR
from modules.indicator.sma import SMA


class IndicatorFactory:
    """
    Factory class for creating indicator instances.

    This factory follows the Open/Closed Principle by making it easy to add
    new indicators without modifying existing code.
    """

    # Registry of available indicators
    _indicator_registry: Dict[str, Type[Indicator]] = {
        "SMA": SMA,
        "EMA": EMA,
        "ParabolicSAR": ParabolicSAR,
    }

    @classmethod
    def create_indicator(
        cls,
        indicator_type: str,
        indicator_manager: IndicatorManager,
        **kwargs: Any,
    ) -> Indicator:
        """
        Create an indicator instance.

        Args:
            indicator_type: Indicator type identifier (e.g., "SMA", "EMA", "ParabolicSAR")
            symbol: Trading pair symbol
            indicator_manager: IndicatorManager instance
            **kwargs: Additional parameters for the specific indicator
                      (e.g., period for SMA/EMA, acceleration/maximum for ParabolicSAR)

        Returns:
            Initialized Indicator instance

        Raises:
            ValueError: If indicator type is not supported
        """
        indicator_type_upper = indicator_type.upper()

        if indicator_type_upper not in cls._indicator_registry:
            raise ValueError(
                f"Unsupported indicator: {indicator_type}. "
                f"Supported indicators: {list[str](cls._indicator_registry.keys())}"
            )

        indicator_class = cls._indicator_registry[indicator_type_upper]
        indicator = indicator_class(indicator_manager, **kwargs)

        # Registration happens in indicator __init__, no need to register again
        return indicator

    @classmethod
    def get_supported_indicators(cls) -> list:
        """
        Get list of supported indicator types.

        Returns:
            List of indicator type identifiers
        """
        return list(cls._indicator_registry.keys())

    @classmethod
    def is_supported(cls, indicator_type: str) -> bool:
        """
        Check if an indicator type is supported.

        Args:
            indicator_type: Indicator type identifier

        Returns:
            True if supported, False otherwise
        """
        return indicator_type.upper() in cls._indicator_registry

    @classmethod
    def register_indicator(
        cls, indicator_type: str, indicator_class: Type[Indicator]
    ) -> None:
        """
        Register a custom indicator class.

        This allows extending the factory with new indicators.

        Args:
            indicator_type: Indicator type identifier
            indicator_class: Indicator class to register
        """
        cls._indicator_registry[indicator_type.upper()] = indicator_class

    @classmethod
    def unregister_indicator(cls, indicator_type: str) -> None:
        """
        Unregister an indicator class.

        Args:
            indicator_type: Indicator type identifier
        """
        cls._indicator_registry.pop(indicator_type.upper(), None)

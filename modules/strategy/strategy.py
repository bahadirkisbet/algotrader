from abc import ABC, abstractmethod
from typing import Any, Dict


class Strategy(ABC):
    """Abstract base class for all trading strategies."""

    @abstractmethod
    def train(self, training_data: Any) -> None:
        """Train the strategy with historical data."""
        pass

    @abstractmethod
    def predict(self, market_data: Any) -> Dict[str, Any]:
        """Generate trading predictions based on current market data."""
        pass

    @abstractmethod
    def should_buy(self, market_data: Any) -> bool:
        """Determine if the strategy suggests buying."""
        pass

    @abstractmethod
    def should_sell(self, market_data: Any) -> bool:
        """Determine if the strategy suggests selling."""
        pass

    @abstractmethod
    def get_confidence(self, market_data: Any) -> float:
        """Get the confidence level of the current prediction (0.0 to 1.0)."""
        pass

    def get_strategy_name(self) -> str:
        """Get the name of this strategy."""
        return self.__class__.__name__

    def get_parameters(self) -> Dict[str, Any]:
        """Get the current strategy parameters."""
        return {}

    def set_parameters(self, parameters: Dict[str, Any]) -> None:
        """Set strategy parameters."""
        pass

    def reset(self) -> None:
        """Reset the strategy to its initial state."""
        pass


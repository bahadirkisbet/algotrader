"""
Parabolic SAR (Stop and Reverse) Technical Indicator.
"""

from typing import Optional

from modules.data.candle import Candle
from modules.indicator.base import Indicator


class ParabolicSAR(Indicator):
    """
    Parabolic SAR (Stop and Reverse) indicator.

    The indicator is designed to determine the direction of a trend and provide
    potential entry/exit signals. When the dots flip from above to below the price,
    it's a buy signal. When they flip from below to above, it's a sell signal.

    Note: Parabolic SAR requires state to track trend, extreme points, and acceleration.
    The required state is stored internally.

    Parameters:
        symbol: Trading pair symbol
        indicator_manager: IndicatorManager instance
        acceleration: Initial acceleration factor (default: 0.02)
        maximum: Maximum acceleration factor (default: 0.20)
    """

    def __init__(
        self,
        symbol: str,
        indicator_manager: object,
        acceleration: float = 0.02,
        maximum: float = 0.20,
    ):
        super().__init__(symbol, indicator_manager)

        # Configuration
        self.initial_acceleration = acceleration
        self.maximum_acceleration = maximum
        self.code = f"psar_{int(acceleration * 100)}_{int(maximum * 100)}"

        # State variables (required for ParabolicSAR calculation)
        self.is_long = True  # True = uptrend, False = downtrend
        self.acceleration_factor = self.initial_acceleration
        self.extreme_point = None  # Highest high in uptrend, lowest low in downtrend
        self.current_sar = None
        self.previous_candle = None
        self.initialized = False

        self.register()

    def calculate(self, candle: Candle, index: Optional[int] = None) -> Optional[float]:
        """Calculate Parabolic SAR for the given candle."""
        if not self.initialized:
            return self._initialize(candle)

        # Calculate new SAR
        new_sar = self._calculate_sar(candle)

        # Check for trend reversal
        if self._check_reversal(candle, new_sar):
            new_sar = self._reverse_trend(candle)
        else:
            # Update acceleration factor and extreme point
            self._update_trend(candle)

        # Store the result
        self.current_sar = new_sar
        self.previous_candle = candle
        self.data.append([candle.timestamp, new_sar])

        return new_sar

    def _initialize(self, candle: Candle) -> Optional[float]:
        """Initialize the indicator with the first candle."""
        self.is_long = True
        self.current_sar = candle.low
        self.extreme_point = candle.high

        self.acceleration_factor = self.initial_acceleration
        self.previous_candle = candle
        self.initialized = True
        self.data.append([candle.timestamp, self.current_sar])

        return self.current_sar

    def _calculate_sar(self, candle: Candle) -> float:
        """Calculate new SAR value."""
        sar = self.current_sar + self.acceleration_factor * (self.extreme_point - self.current_sar)

        # Ensure SAR doesn't enter the price range of the last two periods
        if self.is_long:
            if self.previous_candle:
                sar = min(sar, self.previous_candle.low, candle.low)
        else:
            if self.previous_candle:
                sar = max(sar, self.previous_candle.high, candle.high)

        return sar

    def _check_reversal(self, candle: Candle, new_sar: float) -> bool:
        """Check if a trend reversal has occurred."""
        if self.is_long:
            return candle.low < new_sar
        else:
            return candle.high > new_sar

    def _reverse_trend(self, candle: Candle) -> float:
        """Handle trend reversal."""
        self.is_long = not self.is_long
        self.acceleration_factor = self.initial_acceleration

        if self.is_long:
            new_sar = self.extreme_point
            self.extreme_point = candle.high
        else:
            new_sar = self.extreme_point
            self.extreme_point = candle.low

        return new_sar

    def _update_trend(self, candle: Candle) -> None:
        """Update trend parameters (AF and EP) if no reversal occurred."""
        ep_updated = False

        if self.is_long:
            if candle.high > self.extreme_point:
                self.extreme_point = candle.high
                ep_updated = True
        else:
            if candle.low < self.extreme_point:
                self.extreme_point = candle.low
                ep_updated = True

        # Increase acceleration factor if extreme point was updated
        if ep_updated:
            self.acceleration_factor = min(
                self.acceleration_factor + self.initial_acceleration,
                self.maximum_acceleration,
            )

    def get_trend(self) -> str:
        """Get current trend direction."""
        if not self.initialized:
            return "UNKNOWN"
        return "LONG" if self.is_long else "SHORT"

    def is_buy_signal(self, candle: Candle) -> bool:
        """Check if current candle shows a buy signal."""
        if not self.initialized or not self.previous_candle:
            return False
        return not self.is_long and candle.close > self.current_sar

    def is_sell_signal(self, candle: Candle) -> bool:
        """Check if current candle shows a sell signal."""
        if not self.initialized or not self.previous_candle:
            return False
        return self.is_long and candle.close < self.current_sar

    def print(self, index: int = 0, reverse: bool = True) -> None:
        """Print indicator information."""
        value = self.get(index, reverse)
        trend = self.get_trend()
        self.logger.info(
            "%s %s: %.8f (Trend: %s, AF: %.3f)",
            self.symbol,
            self.__class__.__name__,
            value,
            trend,
            self.acceleration_factor,
        )

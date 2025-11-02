"""
Exponential Moving Average (EMA) indicator implementation.
"""

from typing import Optional

from modules.data.candle import Candle
from modules.indicator.base import Indicator


class EMA(Indicator):
    """
    Exponential Moving Average indicator.

    Calculates the EMA giving more weight to recent prices.
    Uses IndicatorManager to efficiently fetch previous EMA values.
    """

    def __init__(
        self,
        symbol: str,
        indicator_manager: object,
        period: int = 9,
    ):
        """
        Initialize EMA indicator.

        Args:
            symbol: Trading pair symbol
            indicator_manager: IndicatorManager instance
            period: Number of periods for EMA calculation
        """
        super().__init__(symbol, indicator_manager)
        self.period = period
        self.code = f"ema_{self.period}"
        self.alpha = 2.0 / (self.period + 1)
        self.register()

    def calculate(self, candle: Candle, index: Optional[int] = None) -> Optional[float]:
        """
        Calculate EMA for a single candle using previous EMA value for efficiency.

        Args:
            candle: Current candle to calculate for
            index: Optional index of current candle

        Returns:
            EMA value or None if insufficient data
        """
        # Try to get previous EMA value
        previous_ema = self.get_previous_indicator_value(self.code, index=1, reverse=False)

        if previous_ema is not None:
            # We have previous EMA, use it for efficient calculation
            ema = (candle.close * self.alpha) + (previous_ema * (1 - self.alpha))
            self.data.append([candle.timestamp, ema])
            return ema

        # No previous EMA, need to calculate from scratch
        # Collect enough historical candles for SMA initialization
        candles_to_use = []
        for i in range(self.period):
            historical_candle = self.indicator_manager.request_candle(
                self.symbol, i + 1, reverse=True
            )
            if historical_candle is None:
                # Not enough data, use simple approach
                result = candle.close
                self.data.append([candle.timestamp, result])
                return result
            candles_to_use.append(historical_candle)
        # Add current candle at the end
        candles_to_use.append(candle)

        # Calculate initial SMA from first 'period' historical candles
        total = sum(c.close for c in candles_to_use[: self.period])
        sma = total / self.period

        # Apply EMA formula to current candle
        ema = (candle.close * self.alpha) + (sma * (1 - self.alpha))

        self.data.append([candle.timestamp, ema])
        return ema

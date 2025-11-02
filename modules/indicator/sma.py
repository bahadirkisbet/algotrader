"""
Simple Moving Average (SMA) indicator implementation.
"""

from typing import Optional

from modules.data.candle import Candle
from modules.indicator.base import Indicator


class SMA(Indicator):
    """
    Simple Moving Average indicator.

    Calculates the average of the last N candles' close prices.
    Uses IndicatorManager to request historical candle data.
    """

    def __init__(
        self,
        symbol: str,
        indicator_manager: object,
        period: int = 14,
    ):
        """
        Initialize SMA indicator.

        Args:
            symbol: Trading pair symbol
            indicator_manager: IndicatorManager instance
            period: Number of periods for moving average
        """
        super().__init__(symbol, indicator_manager)
        self.period = period
        self.code = f"sma_{self.period}"
        self.register()

    def calculate(self, candle: Candle, index: Optional[int] = None) -> Optional[float]:
        """
        Calculate SMA for a single candle.

        Args:
            candle: Current candle to calculate for
            index: Optional index of current candle

        Returns:
            SMA value or None if insufficient data
        """
        # Collect the last 'period' candles including current
        candles_to_use = []

        # Request candles backwards from current
        for i in range(self.period):
            historical_candle = self.indicator_manager.request_candle(
                self.symbol, i + 1, reverse=True
            )
            if historical_candle is None:
                # Not enough data
                self.data.append([candle.timestamp, None])
                return None
            candles_to_use.append(historical_candle)
        # Add current candle
        candles_to_use.append(candle)

        # Calculate average of close prices
        total = sum(c.close for c in candles_to_use)
        result = total / self.period
        self.data.append([candle.timestamp, result])
        return result

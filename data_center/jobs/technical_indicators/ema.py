from typing import Callable, Optional

from data_center.jobs.technical_indicator import DataCenterIndicator
from models.data_models.candle import Candle


class ExponentialMovingAverage(DataCenterIndicator):
    def __init__(self, symbol: str, request_callback: Callable, period: int = 9):
        super().__init__(symbol, request_callback)
        self.period = period
        self.code = f"ema_{self.period}"
        self.registry[f"{self.symbol}_{self.code}"] = self
        self.alpha = 2.0 / (self.period + 1)
        self.previous_ema = None

    def calculate(self, candle: Candle, index: Optional[int] = None) -> Optional[float]:
        if index is None:
            historical_index = self.period
            from_back = True
        else:
            historical_index = index - self.period
            from_back = False

        previous_candle = self.request_callback(self.symbol, historical_index, from_back)
        if previous_candle is not None:
            ema = self.alpha * candle.close + (1 - self.alpha) * self.previous_ema
        else:  # it does not reach to the value to calculate the average properly
            ema = candle.close

        self.previous_ema = ema
        self.data.append([candle.timestamp, ema])
        return ema

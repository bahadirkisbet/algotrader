from typing import Callable, Optional

from data_center.jobs.technical_indicator import DataCenterIndicator
from models.data_models.candle import Candle


class SimpleMovingAverage(DataCenterIndicator):
    def __init__(self, symbol: str, request_callback: Callable, period: int = 14):
        super().__init__(symbol, request_callback)
        self.period = period
        self.total_sum = 0
        self.total_count = 0
        self.code = f"sma_{self.period}"
        self.registry[f"{self.symbol}_{self.code}"] = self

    def calculate(self, candle: Candle, index: Optional[int] = None) -> Optional[float]:
        if index is None:
            historical_index = self.period
            from_back = True
        else:
            historical_index = index - self.period
            from_back = False

        previous_candle = self.request_callback(self.symbol, historical_index, from_back)

        if previous_candle is not None:
            self.total_sum -= previous_candle.close
        else:  # it does not reach to the value to calculate the average properly
            self.total_count += 1

        self.total_sum += candle.close
        current_value = self.total_sum / self.period if self.total_count >= self.period else None
        self.data.append([candle.timestamp, current_value])
        return current_value

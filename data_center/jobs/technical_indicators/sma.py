from typing import Callable, Optional

from common_models.data_models.candle import Candle
from data_center.jobs.technical_indicator import TechnicalIndicator


class SimpleMovingAverage(TechnicalIndicator):
    def __init__(self, symbol: str, request_callback: Callable, period: int):
        super().__init__(symbol, request_callback)
        self.period = period
        self.__total_sum__ = 0
        self.__total_count__ = 0
        self.__registry__[f"{self.symbol}_{self.period}"] = self

    def calculate(self, candle: Candle, index: int = 0) -> Optional[float]:
        previous_candle = self.request_callback(self.symbol, self.period + index + 1)
        if previous_candle is not None:
            self.__total_sum__ -= previous_candle.close
        else:  # it does not reach to the value to calculate the average properly
            self.__total_count__ += 1
        self.__total_sum__ += candle.close
        current_value = self.__total_sum__ / self.period if self.__total_count__ >= self.period else None
        self.data.append([candle.timestamp, current_value])
        return current_value

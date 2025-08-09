from typing import Callable, Optional

from models.data_models.candle import Candle
from data_center.jobs.technical_indicator import TechnicalIndicator


class SimpleMovingAverage(TechnicalIndicator):
    def __init__(self, symbol: str, request_callback: Callable, period: int = 14):
        super().__init__(symbol, request_callback)
        self.period = period
        self.__total_sum__ = 0
        self.__total_count__ = 0
        self.code = f"sma_{self.period}"
        self.__registry__[f"{self.symbol}_{self.code}"] = self

    def calculate(self, candle: Candle, index: Optional[int] = None) -> Optional[float]:
        if index is None:
            historical_index = self.period
            from_back = True
        else:
            historical_index = index - self.period
            from_back = False

        previous_candle = self.request_callback(self.symbol, historical_index, from_back)

        if previous_candle is not None:
            self.__total_sum__ -= previous_candle.close
        else:  # it does not reach to the value to calculate the average properly
            self.__total_count__ += 1

        self.__total_sum__ += candle.close
        current_value = self.__total_sum__ / self.period if self.__total_count__ >= self.period else None
        self.data.append([candle.timestamp, current_value])
        return current_value

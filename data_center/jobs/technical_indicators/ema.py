from typing import Callable, Optional

from data_center.jobs.technical_indicator import TechnicalIndicator
from models.data_models.candle import Candle


class ExponentialMovingAverage(TechnicalIndicator):
    def __init__(self, symbol: str, request_callback: Callable, period: int = 9):
        super().__init__(symbol, request_callback)
        self.period = period
        self.code = f"ema_{self.period}"
        self.__registry__[f"{self.symbol}_{self.code}"] = self
        self.__alpha__ = 2.0 / (self.period + 1)
        self.__prev_ema__ = None

    def calculate(self, candle: Candle, index: Optional[int] = None) -> Optional[float]:
        if index is None:
            historical_index = self.period
            from_back = True
        else:
            historical_index = index - self.period
            from_back = False

        previous_candle = self.request_callback(self.symbol, historical_index, from_back)
        if previous_candle is not None:
            ema = self.__alpha__ * candle.close + (1 - self.__alpha__) * self.__prev_ema__
        else:  # it does not reach to the value to calculate the average properly
            ema = candle.close

        self.__prev_ema__ = ema
        self.data.append([candle.timestamp, ema])
        return ema

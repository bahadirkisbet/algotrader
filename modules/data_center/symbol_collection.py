from typing import List, Optional

from modules.indicator.indicator_manager import IndicatorManager
from modules.model.candle import Candle
from modules.model.interval import Interval


class SymbolCollection:
    def __init__(self, symbol: str, interval: Interval, indicators: List[object]):
        assert symbol is not None, "Symbol is required"
        assert interval is not None, "Interval is required"
        assert indicators is not None, "Indicators are required"
        self.symbol = symbol
        self.interval = interval
        self.indicator_manager = IndicatorManager(
            candle_request_callback=self.get_candle, indicators=indicators
        )
        self.candles: List[Candle] = []

    def get_candle(self, index: int = 0, reverse: bool = False) -> Optional[Candle]:
        if reverse:
            return self.candles[-1 - index]
        return self.candles[index]

    def add_candle(self, candle: Candle) -> None:
        self.candles.append(candle)
        self.indicator_manager.calculate(candle)

    def get_symbol_code(self) -> str:
        return f"{self.symbol}@{self.interval}"

    def get_indicator_value(
        self, code: str, index: int = 0, reverse: bool = False
    ) -> Optional[object]:
        candle = self.get_candle(index, reverse)
        if candle is None:
            return None
        return candle.get(code)

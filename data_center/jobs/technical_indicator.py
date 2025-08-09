import logging
from abc import ABC, abstractmethod
from typing import Callable, Optional

from models.data_models.candle import Candle
from utils.di_container import get


class TechnicalIndicator(ABC):
    __registry__ = {}

    def __init__(self, symbol: str, request_callback: Callable):
        self.logger: logging.Logger = get(logging.Logger)

        self.symbol: str = symbol
        self.request_callback: Callable = request_callback

        # Dependency priority is used to determine the order of calculation of technical indicators.
        self.dependency_priority: int = 0
        self.data: list = []
        self.code: str = "NotSet"

    @staticmethod
    def get_instance(symbol, code):
        return TechnicalIndicator.__registry__.get(f"{symbol}_{code}", None)

    @abstractmethod
    def calculate(self, candle: Candle, index: int = 0) -> Optional[float]:
        pass

    def plot(self):
        pass

    def get(self, index: int = 0, reverse: bool = False) -> float:
        return self.data[-1 - index if reverse else index][1]

    def print(self, index: int = 0, reverse: bool = True) -> None:
        self.logger.info(f"{self.symbol} {self.__class__.__name__} {self.get(index, reverse)}")

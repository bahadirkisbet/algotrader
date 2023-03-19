from abc import ABC
from typing import Callable


class TechnicalIndicator(ABC):
    __registry__ = {}

    def __init__(self, symbol: str, request_callback: Callable):
        self.symbol: str = symbol
        self.request_callback: Callable = request_callback
        self.dependency_priority: int = 0
        self.data: list = []

    @staticmethod
    def get_instance(symbol, period):
        return TechnicalIndicator.__registry__.get(f"{symbol}_{period}", None)

    def plot(self):
        pass

    def get(self, index_offset=0):
        return self.data[-1 - index_offset][1]  # reverse indexing

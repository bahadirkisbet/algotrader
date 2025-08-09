import configparser
import logging
from typing import List

from strategy_provider.strategy import Strategy

from utils.di_container import get
from utils.singleton_metaclass.singleton import Singleton


class StrategyCenter(metaclass=Singleton):
    strategies: List[Strategy] = []

    def __init__(self):
        self.logger: logging.Logger = get(logging.Logger)
        self.config: configparser.ConfigParser = get(configparser.ConfigParser)

    def backtest(self):
        pass

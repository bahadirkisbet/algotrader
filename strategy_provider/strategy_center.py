import configparser
import logging
from typing import List

from managers.service_manager import ServiceManager
from strategy_provider.strategy import Strategy
from utils.singleton_metaclass.singleton import Singleton


class StrategyCenter(metaclass=Singleton):
    __backtest__: bool = True
    strategies: List[Strategy] = []

    def __init__(self):
        self.logger: logging.Logger = ServiceManager.get_service("logger")
        self.config: configparser.ConfigParser = ServiceManager.get_service("config")

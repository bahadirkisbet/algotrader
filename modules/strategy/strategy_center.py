import configparser
import logging
from typing import List

from strategy.strategy import Strategy

from utils.dependency_injection_container import get
from utils.singleton_metaclass.singleton import Singleton


class TradingStrategyManager(metaclass=Singleton):
    """Central manager for all trading strategies."""
    
    strategies: List[Strategy] = []

    def __init__(self):
        self.logger: logging.Logger = get(logging.Logger)
        self.config: configparser.ConfigParser = get(configparser.ConfigParser)

    def add_strategy(self, strategy: Strategy) -> None:
        """Add a new strategy to the manager."""
        if strategy not in self.strategies:
            self.strategies.append(strategy)
            self.logger.info(f"Added strategy: {strategy.__class__.__name__}")

    def remove_strategy(self, strategy: Strategy) -> None:
        """Remove a strategy from the manager."""
        if strategy in self.strategies:
            self.strategies.remove(strategy)
            self.logger.info(f"Removed strategy: {strategy.__class__.__name__}")

    def get_all_strategies(self) -> List[Strategy]:
        """Get all registered strategies."""
        return self.strategies.copy()

    def get_strategy_by_name(self, name: str) -> Strategy:
        """Get a strategy by its name."""
        for strategy in self.strategies:
            if strategy.__class__.__name__ == name:
                return strategy
        raise ValueError(f"Strategy '{name}' not found")

    def run_backtest_for_all_strategies(self):
        """Run backtesting for all strategies."""
        pass

    def start_all_strategies(self):
        """Start all registered strategies."""
        pass

    def stop_all_strategies(self):
        """Stop all registered strategies."""
        pass

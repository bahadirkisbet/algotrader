"""
Simulation and Backtesting Module.

This module provides a comprehensive backtesting framework similar to TradingView's strategy tester.
"""

from simulations.config import SimulationConfig
from simulations.engine import SimulationEngine
from simulations.performance import PerformanceMetrics, PerformanceReport
from simulations.portfolio import Portfolio, Position, Trade

__all__ = [
    "SimulationConfig",
    "SimulationEngine",
    "PerformanceMetrics",
    "PerformanceReport",
    "Portfolio",
    "Position",
    "Trade",
]

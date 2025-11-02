"""
Simulation Configuration.

This module defines the configuration options for running backtests,
similar to TradingView's strategy tester settings.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from models.exchange_type import ExchangeType
from models.time_models import Interval


@dataclass
class SimulationConfig:
    """
    Configuration for simulation runs (similar to TradingView Strategy Tester).

    This class holds all the parameters needed to run a backtest:
    - Symbol and Exchange settings
    - Time range and interval
    - Capital and risk management
    - Fees and slippage
    - Strategy parameters
    """

    # --- Market Settings (Required) ---
    symbol: str  # Trading pair (e.g., "BTCUSDT")
    exchange: str  # Exchange name (e.g., "BINANCE")
    exchange_type: ExchangeType = ExchangeType.SPOT  # SPOT or FUTURES
    interval: Interval = Interval.ONE_HOUR  # Candle interval

    # --- Time Range (Required) ---
    start_date: datetime = None  # Backtest start date
    end_date: datetime = None  # Backtest end date

    # --- Capital Management ---
    initial_capital: float = 10000.0  # Starting capital in USD
    position_size_pct: float = 1.0  # % of capital per trade (100% = all-in)
    max_position_size: Optional[float] = None  # Maximum position size in USD

    # --- Fees and Costs ---
    commission_rate: float = 0.001  # 0.1% commission (typical for exchanges)
    slippage_pct: float = 0.0  # Price slippage percentage
    maker_fee: Optional[float] = None  # Maker fee (if different from commission)
    taker_fee: Optional[float] = None  # Taker fee (if different from commission)

    # --- Risk Management ---
    stop_loss_pct: Optional[float] = None  # Stop loss percentage
    take_profit_pct: Optional[float] = None  # Take profit percentage
    max_drawdown_pct: Optional[float] = None  # Stop trading if drawdown exceeds this
    max_daily_loss_pct: Optional[float] = None  # Maximum daily loss allowed

    # --- Strategy Settings ---
    strategy_name: str = "UnnamedStrategy"  # Name of the strategy
    strategy_params: dict = field(default_factory=dict)  # Strategy-specific parameters

    # --- Execution Settings ---
    order_type: str = "market"  # "market" or "limit"
    allow_partial_fills: bool = True  # Allow partial order fills
    min_order_size: Optional[float] = None  # Minimum order size

    # --- Reporting and Output ---
    save_results: bool = True  # Save results to file
    output_directory: str = "simulation_results"  # Output directory
    generate_charts: bool = True  # Generate performance charts
    verbose: bool = True  # Print detailed logs

    # --- Advanced Settings ---
    compound_returns: bool = True  # Reinvest profits
    pyramid: bool = False  # Allow pyramiding (adding to winning positions)
    max_pyramiding: int = 1  # Maximum number of pyramid orders
    use_limit_orders: bool = False  # Use limit orders instead of market
    limit_order_offset_pct: float = 0.1  # Offset for limit orders

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.start_date is None:
            raise ValueError("start_date is required")
        if self.end_date is None:
            raise ValueError("end_date is required")
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        if not 0 < self.position_size_pct <= 1:
            raise ValueError("position_size_pct must be between 0 and 1")
        if self.commission_rate < 0:
            raise ValueError("commission_rate cannot be negative")

        # Set maker/taker fees if not specified
        if self.maker_fee is None:
            self.maker_fee = self.commission_rate
        if self.taker_fee is None:
            self.taker_fee = self.commission_rate

    def get_effective_commission(self, is_maker: bool = False) -> float:
        """Get the effective commission rate for a trade."""
        return self.maker_fee if is_maker else self.taker_fee

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            # Market Settings
            "symbol": self.symbol,
            "exchange": self.exchange,
            "exchange_type": self.exchange_type.value
            if hasattr(self.exchange_type, "value")
            else str(self.exchange_type),
            "interval": str(self.interval),
            # Time Range
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "duration_days": (self.end_date - self.start_date).days,
            # Capital
            "initial_capital": self.initial_capital,
            "position_size_pct": self.position_size_pct * 100,
            # Fees
            "commission_rate": self.commission_rate * 100,
            "slippage_pct": self.slippage_pct * 100,
            # Risk Management
            "stop_loss_pct": self.stop_loss_pct * 100 if self.stop_loss_pct else None,
            "take_profit_pct": self.take_profit_pct * 100 if self.take_profit_pct else None,
            # Strategy
            "strategy_name": self.strategy_name,
            "strategy_params": self.strategy_params,
        }

    def __repr__(self) -> str:
        """String representation of configuration."""
        return (
            f"SimulationConfig("
            f"symbol={self.symbol}, "
            f"exchange={self.exchange}, "
            f"interval={self.interval}, "
            f"period={self.start_date.date()} to {self.end_date.date()}, "
            f"capital=${self.initial_capital:,.0f})"
        )


@dataclass
class MultiSymbolConfig(SimulationConfig):
    """
    Configuration for multi-symbol backtesting.

    Allows testing strategies across multiple symbols simultaneously.
    """

    symbols: List[str] = field(default_factory=list)  # List of symbols to trade
    symbol_weights: Optional[dict] = None  # Weight allocation per symbol

    def __post_init__(self):
        """Validate multi-symbol configuration."""
        super().__post_init__()

        if not self.symbols:
            self.symbols = [self.symbol]

        # Validate symbol weights
        if self.symbol_weights:
            total_weight = sum(self.symbol_weights.values())
            if abs(total_weight - 1.0) > 0.01:
                raise ValueError(f"Symbol weights must sum to 1.0, got {total_weight}")

            for symbol in self.symbols:
                if symbol not in self.symbol_weights:
                    raise ValueError(f"Missing weight for symbol: {symbol}")
        else:
            # Equal weight allocation
            weight = 1.0 / len(self.symbols)
            self.symbol_weights = {s: weight for s in self.symbols}


def create_default_config(
    symbol: str,
    exchange: str = "BINANCE",
    start_date: datetime = None,
    end_date: datetime = None,
    **kwargs,
) -> SimulationConfig:
    """
    Create a default simulation configuration with sensible defaults.

    Args:
        symbol: Trading symbol
        exchange: Exchange name
        start_date: Start date for backtest
        end_date: End date for backtest
        **kwargs: Additional configuration parameters

    Returns:
        SimulationConfig instance
    """
    if start_date is None:
        from datetime import timedelta

        end_date = end_date or datetime.now()
        start_date = end_date - timedelta(days=365)  # Default: 1 year

    if end_date is None:
        end_date = datetime.now()

    return SimulationConfig(
        symbol=symbol, exchange=exchange, start_date=start_date, end_date=end_date, **kwargs
    )

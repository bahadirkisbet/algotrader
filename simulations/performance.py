"""
Performance Metrics and Reporting.

This module calculates trading performance metrics and generates reports
similar to TradingView's strategy tester output.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

import numpy as np

from simulations.portfolio import Portfolio, Trade


@dataclass
class PerformanceMetrics:
    """
    Comprehensive performance metrics for backtesting.

    Contains all key metrics similar to TradingView's strategy tester:
    - Returns and P&L
    - Risk metrics
    - Trade statistics
    - Ratios and efficiency
    """

    # Returns
    total_return_pct: float = 0.0
    annualized_return_pct: float = 0.0
    total_pnl: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0

    # Risk Metrics
    max_drawdown_pct: float = 0.0
    max_drawdown_duration_days: int = 0
    volatility_pct: float = 0.0
    downside_deviation_pct: float = 0.0

    # Trade Statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate_pct: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0

    # Efficiency Ratios
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    profit_factor: float = 0.0

    # Time Metrics
    avg_trade_duration_hours: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0

    # Costs
    total_commission: float = 0.0
    total_slippage: float = 0.0
    commission_pct_of_pnl: float = 0.0

    # Additional Metrics
    recovery_factor: float = 0.0  # Net profit / Max drawdown
    expectancy: float = 0.0  # Average expected profit per trade

    def to_dict(self) -> dict:
        """Convert metrics to dictionary."""
        return {
            # Returns
            "total_return_pct": round(self.total_return_pct, 2),
            "annualized_return_pct": round(self.annualized_return_pct, 2),
            "total_pnl": round(self.total_pnl, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            # Risk
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "max_drawdown_duration_days": self.max_drawdown_duration_days,
            "volatility_pct": round(self.volatility_pct, 2),
            # Trades
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate_pct": round(self.win_rate_pct, 2),
            "avg_win": round(self.avg_win, 2),
            "avg_loss": round(self.avg_loss, 2),
            "largest_win": round(self.largest_win, 2),
            "largest_loss": round(self.largest_loss, 2),
            # Ratios
            "sharpe_ratio": round(self.sharpe_ratio, 3),
            "sortino_ratio": round(self.sortino_ratio, 3),
            "calmar_ratio": round(self.calmar_ratio, 3),
            "profit_factor": round(self.profit_factor, 2),
            # Other
            "total_commission": round(self.total_commission, 2),
            "total_slippage": round(self.total_slippage, 2),
            "expectancy": round(self.expectancy, 2),
        }


class PerformanceCalculator:
    """Calculate performance metrics from portfolio data."""

    @staticmethod
    def calculate(
        portfolio: Portfolio,
        start_date: datetime,
        end_date: datetime,
        risk_free_rate: float = 0.02,  # 2% annual risk-free rate
    ) -> PerformanceMetrics:
        """
        Calculate all performance metrics.

        Args:
            portfolio: Portfolio instance
            start_date: Backtest start date
            end_date: Backtest end date
            risk_free_rate: Annual risk-free rate for Sharpe calculation

        Returns:
            PerformanceMetrics instance
        """
        metrics = PerformanceMetrics()

        # Basic metrics from portfolio
        summary = portfolio.get_summary()
        metrics.total_pnl = summary["total_pnl"]
        metrics.realized_pnl = summary["realized_pnl"]
        metrics.unrealized_pnl = summary["unrealized_pnl"]
        metrics.total_trades = summary["total_trades"]
        metrics.winning_trades = summary["winning_trades"]
        metrics.losing_trades = summary["losing_trades"]
        metrics.win_rate_pct = summary["win_rate_pct"]
        metrics.total_commission = summary["total_commission"]
        metrics.total_slippage = summary["total_slippage"]

        # Returns
        metrics.total_return_pct = summary["total_return_pct"]
        duration_years = (end_date - start_date).days / 365.25
        if duration_years > 0:
            metrics.annualized_return_pct = (
                (1 + metrics.total_return_pct / 100) ** (1 / duration_years) - 1
            ) * 100

        # Calculate trade-based metrics
        if portfolio.trade_history:
            metrics = PerformanceCalculator._calculate_trade_metrics(
                metrics, portfolio.trade_history
            )

        # Calculate equity curve metrics
        if len(portfolio.equity_curve) > 1:
            metrics = PerformanceCalculator._calculate_equity_metrics(
                metrics, portfolio.equity_curve, portfolio.initial_capital, risk_free_rate
            )

        # Calculate drawdown metrics
        metrics = PerformanceCalculator._calculate_drawdown_metrics(
            metrics, portfolio.equity_curve, portfolio.equity_timestamps
        )

        # Calculate ratios
        if metrics.max_drawdown_pct > 0:
            metrics.calmar_ratio = metrics.annualized_return_pct / metrics.max_drawdown_pct
            metrics.recovery_factor = metrics.total_pnl / (
                portfolio.peak_equity * metrics.max_drawdown_pct / 100
            )

        # Commission impact
        if metrics.total_pnl != 0:
            metrics.commission_pct_of_pnl = (
                metrics.total_commission / abs(metrics.total_pnl)
            ) * 100

        return metrics

    @staticmethod
    def _calculate_trade_metrics(
        metrics: PerformanceMetrics, trades: List[Trade]
    ) -> PerformanceMetrics:
        """Calculate metrics from trade history."""
        # Track entry/exit pairs to calculate P&L
        positions = {}
        trade_pnls = []
        wins = []
        losses = []

        for trade in trades:
            if trade.side.value == "buy":
                # Opening position
                if trade.symbol not in positions:
                    positions[trade.symbol] = []
                positions[trade.symbol].append(
                    {
                        "quantity": trade.quantity,
                        "price": trade.price,
                        "cost": trade.total_cost,
                        "timestamp": trade.timestamp,
                    }
                )
            else:
                # Closing position
                if trade.symbol in positions and positions[trade.symbol]:
                    pos = positions[trade.symbol].pop(0)
                    proceeds = (trade.quantity * trade.price) - trade.commission - trade.slippage
                    pnl = proceeds - pos["cost"]
                    trade_pnls.append(pnl)

                    if pnl > 0:
                        wins.append(pnl)
                    elif pnl < 0:
                        losses.append(pnl)

                    # Calculate trade duration
                    if hasattr(trade, "timestamp") and hasattr(pos["timestamp"], "timestamp"):
                        duration = (trade.timestamp - pos["timestamp"]).total_seconds() / 3600
                        if duration > 0:
                            if not hasattr(metrics, "_durations"):
                                metrics._durations = []
                            metrics._durations.append(duration)

        # Calculate averages and extremes
        if wins:
            metrics.avg_win = sum(wins) / len(wins)
            metrics.largest_win = max(wins)

        if losses:
            metrics.avg_loss = sum(losses) / len(losses)
            metrics.largest_loss = min(losses)

        # Profit factor
        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 0
        if total_losses > 0:
            metrics.profit_factor = total_wins / total_losses

        # Expectancy
        if trade_pnls:
            metrics.expectancy = sum(trade_pnls) / len(trade_pnls)

        # Consecutive wins/losses
        metrics.max_consecutive_wins, metrics.max_consecutive_losses = (
            PerformanceCalculator._calculate_consecutive_trades(trades, positions)
        )

        # Average trade duration
        if hasattr(metrics, "_durations") and metrics._durations:
            metrics.avg_trade_duration_hours = sum(metrics._durations) / len(metrics._durations)

        return metrics

    @staticmethod
    def _calculate_equity_metrics(
        metrics: PerformanceMetrics,
        equity_curve: List[float],
        _initial_capital: float,
        risk_free_rate: float,
    ) -> PerformanceMetrics:
        """Calculate metrics from equity curve."""
        # Calculate returns
        returns = []
        for i in range(1, len(equity_curve)):
            ret = (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
            returns.append(ret)

        if not returns:
            return metrics

        # Volatility (annualized standard deviation)
        std_return = np.std(returns)
        metrics.volatility_pct = std_return * np.sqrt(252) * 100  # Annualized

        # Downside deviation (for Sortino ratio)
        negative_returns = [r for r in returns if r < 0]
        if negative_returns:
            downside_std = np.std(negative_returns)
            metrics.downside_deviation_pct = downside_std * np.sqrt(252) * 100

        # Sharpe Ratio
        avg_return = np.mean(returns)
        if std_return > 0:
            # Annualized Sharpe ratio
            excess_return = avg_return * 252 - risk_free_rate
            metrics.sharpe_ratio = excess_return / (std_return * np.sqrt(252))

        # Sortino Ratio
        if negative_returns and metrics.downside_deviation_pct > 0:
            annualized_return = avg_return * 252
            excess_return = annualized_return - risk_free_rate
            metrics.sortino_ratio = excess_return / (metrics.downside_deviation_pct / 100)

        return metrics

    @staticmethod
    def _calculate_drawdown_metrics(
        metrics: PerformanceMetrics,
        equity_curve: List[float],
        timestamps: List[datetime],
    ) -> PerformanceMetrics:
        """Calculate drawdown metrics."""
        if not equity_curve:
            return metrics

        max_drawdown = 0.0
        peak = equity_curve[0]
        peak_idx = 0
        current_dd_start = 0
        max_dd_duration = 0

        for i, equity in enumerate(equity_curve):
            if equity > peak:
                # New peak
                peak = equity
                peak_idx = i
                # Check if we're recovering from a drawdown
                if current_dd_start > 0:
                    dd_duration = i - current_dd_start
                    max_dd_duration = max(max_dd_duration, dd_duration)
                    current_dd_start = 0
            else:
                # In drawdown
                if current_dd_start == 0:
                    current_dd_start = peak_idx

                drawdown = (peak - equity) / peak
                max_drawdown = max(max_drawdown, drawdown)

        metrics.max_drawdown_pct = max_drawdown * 100

        # Convert duration from data points to days
        if timestamps and max_dd_duration > 0:
            # Estimate days based on timestamp intervals
            if len(timestamps) > 1:
                avg_interval_seconds = (timestamps[-1] - timestamps[0]).total_seconds() / len(
                    timestamps
                )
                metrics.max_drawdown_duration_days = int(
                    (max_dd_duration * avg_interval_seconds) / 86400
                )

        return metrics

    @staticmethod
    def _calculate_consecutive_trades(trades: List[Trade], _positions: dict) -> tuple:
        """Calculate maximum consecutive wins and losses."""
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0

        temp_positions = {}

        for trade in trades:
            if trade.side.value == "buy":
                if trade.symbol not in temp_positions:
                    temp_positions[trade.symbol] = []
                temp_positions[trade.symbol].append(
                    {
                        "price": trade.price,
                        "cost": trade.total_cost,
                    }
                )
            else:
                if trade.symbol in temp_positions and temp_positions[trade.symbol]:
                    pos = temp_positions[trade.symbol].pop(0)
                    proceeds = (trade.quantity * trade.price) - trade.commission - trade.slippage
                    pnl = proceeds - pos["cost"]

                    if pnl > 0:
                        current_wins += 1
                        current_losses = 0
                        max_wins = max(max_wins, current_wins)
                    elif pnl < 0:
                        current_losses += 1
                        current_wins = 0
                        max_losses = max(max_losses, current_losses)

        return max_wins, max_losses


class PerformanceReport:
    """Generate performance reports and visualizations."""

    @staticmethod
    def generate_text_report(
        metrics: PerformanceMetrics,
        config,
        portfolio: Portfolio,
    ) -> str:
        """
        Generate a text-based performance report.

        Args:
            metrics: Performance metrics
            config: Simulation configuration
            portfolio: Portfolio instance

        Returns:
            Formatted text report
        """
        report = []
        report.append("=" * 80)
        report.append("BACKTEST PERFORMANCE REPORT")
        report.append("=" * 80)
        report.append("")

        # Configuration
        report.append("CONFIGURATION")
        report.append("-" * 80)
        report.append(f"Strategy:           {config.strategy_name}")
        report.append(f"Symbol:             {config.symbol}")
        report.append(f"Exchange:           {config.exchange}")
        report.append(f"Interval:           {config.interval}")
        report.append(f"Period:             {config.start_date.date()} to {config.end_date.date()}")
        report.append(f"Duration:           {(config.end_date - config.start_date).days} days")
        report.append(f"Initial Capital:    ${config.initial_capital:,.2f}")
        report.append(f"Commission Rate:    {config.commission_rate * 100:.2f}%")
        report.append("")

        # Performance Summary
        report.append("PERFORMANCE SUMMARY")
        report.append("-" * 80)
        report.append(f"Total Return:       {metrics.total_return_pct:+.2f}%")
        report.append(f"Annualized Return:  {metrics.annualized_return_pct:+.2f}%")
        report.append(f"Total P&L:          ${metrics.total_pnl:+,.2f}")
        report.append(f"Final Equity:       ${portfolio.total_equity:,.2f}")
        report.append(f"Peak Equity:        ${portfolio.peak_equity:,.2f}")
        report.append("")

        # Risk Metrics
        report.append("RISK METRICS")
        report.append("-" * 80)
        report.append(f"Max Drawdown:       {metrics.max_drawdown_pct:.2f}%")
        report.append(f"DD Duration:        {metrics.max_drawdown_duration_days} days")
        report.append(f"Volatility:         {metrics.volatility_pct:.2f}%")
        report.append(f"Sharpe Ratio:       {metrics.sharpe_ratio:.3f}")
        report.append(f"Sortino Ratio:      {metrics.sortino_ratio:.3f}")
        report.append(f"Calmar Ratio:       {metrics.calmar_ratio:.3f}")
        report.append("")

        # Trade Statistics
        report.append("TRADE STATISTICS")
        report.append("-" * 80)
        report.append(f"Total Orders:       {metrics.total_trades}")
        closed_trades = metrics.winning_trades + metrics.losing_trades
        report.append(f"Closed Trades:      {closed_trades}")
        report.append(f"Winning Trades:     {metrics.winning_trades}")
        report.append(f"Losing Trades:      {metrics.losing_trades}")
        report.append(f"Win Rate:           {metrics.win_rate_pct:.2f}%")
        report.append(f"Profit Factor:      {metrics.profit_factor:.2f}")
        report.append(f"Avg Win:            ${metrics.avg_win:+,.2f}")
        report.append(f"Avg Loss:           ${metrics.avg_loss:+,.2f}")
        report.append(f"Largest Win:        ${metrics.largest_win:+,.2f}")
        report.append(f"Largest Loss:       ${metrics.largest_loss:+,.2f}")
        report.append(f"Expectancy:         ${metrics.expectancy:+,.2f}")
        report.append("")

        # Costs
        report.append("COSTS")
        report.append("-" * 80)
        report.append(f"Total Commission:   ${metrics.total_commission:,.2f}")
        report.append(f"Total Slippage:     ${metrics.total_slippage:,.2f}")
        report.append(f"Commission % of P&L: {metrics.commission_pct_of_pnl:.2f}%")
        report.append("")

        report.append("=" * 80)

        return "\n".join(report)

    @staticmethod
    def save_report(
        metrics: PerformanceMetrics,
        config,
        portfolio: Portfolio,
        output_dir: str,
    ) -> Path:
        """
        Save performance report to file.

        Args:
            metrics: Performance metrics
            config: Simulation configuration
            portfolio: Portfolio instance
            output_dir: Output directory

        Returns:
            Path to saved report
        """
        # Create directory structure: output_dir/SYMBOL_TIMEFRAME/
        interval_str = str(config.interval).replace("Interval.", "").replace("_", "").lower()
        if hasattr(config.interval, "value"):
            # Map Interval enum values to strings
            interval_map = {1: "1m", 5: "5m", 15: "15m", 30: "30m", 60: "1h", 240: "4h", 1440: "1d"}
            interval_str = interval_map.get(config.interval.value, "1m")

        # Create folder name with symbol, timeframe, and date range
        start_date_str = config.start_date.strftime("%Y%m%d") if config.start_date else "unknown"
        end_date_str = config.end_date.strftime("%Y%m%d") if config.end_date else "unknown"
        symbol_timeframe_dir = f"{config.symbol}_{interval_str}_{start_date_str}_{end_date_str}"
        output_path = Path(output_dir) / symbol_timeframe_dir
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create strategy-specific filename with params
        has_strategy_params = hasattr(config, "strategy_params")
        strategy_params = config.strategy_params if has_strategy_params else {}
        if strategy_params:
            params_str = "_".join([f"{k}_{v}" for k, v in strategy_params.items()])
            strategy_filename = f"{config.strategy_name}_{params_str}_{timestamp}"
        else:
            strategy_filename = f"{config.strategy_name}_{timestamp}"

        # Save text report
        text_report = PerformanceReport.generate_text_report(metrics, config, portfolio)
        text_file = output_path / f"{strategy_filename}_report.txt"
        with open(text_file, "w", encoding="utf-8") as f:
            f.write(text_report)

        # Save JSON data
        json_data = {
            "config": config.to_dict(),
            "metrics": metrics.to_dict(),
            "portfolio_summary": portfolio.get_summary(),
        }
        json_file = output_path / f"{strategy_filename}_data.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, default=str)

        return text_file

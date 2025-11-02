"""
Simulation Engine.

Main engine for running backtests. Orchestrates data fetching, strategy execution,
portfolio management, and performance reporting.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

import matplotlib.pyplot as plt

from models.data_models.candle import Candle
from models.strategy_response import StrategyResponse
from modules.exchange.exchange_factory import ExchangeFactory
from simulations.config import SimulationConfig
from simulations.performance import PerformanceCalculator, PerformanceMetrics, PerformanceReport
from simulations.portfolio import OrderSide, Portfolio


class SimulationEngine:
    """
    Main simulation engine for backtesting trading strategies.

    This engine:
    1. Fetches historical data from exchanges
    2. Runs strategy logic on each candle
    3. Executes trades and manages portfolio
    4. Calculates performance metrics
    5. Generates reports and charts

    Similar to TradingView's strategy tester.
    """

    def __init__(self, config: SimulationConfig):
        """
        Initialize simulation engine.

        Args:
            config: Simulation configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Portfolio management
        self.portfolio = Portfolio(config.initial_capital)

        # Data storage
        self.historical_data: List[Candle] = []
        self.current_candle_index = 0

        # Performance tracking
        self.metrics: Optional[PerformanceMetrics] = None

        # Setup
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        if self.config.verbose:
            logging.basicConfig(
                level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

    async def run(
        self, strategy_function: Callable[[Candle, Dict], StrategyResponse]
    ) -> PerformanceMetrics:
        """
        Run the simulation.

        Args:
            strategy_function: Function that takes (candle, context) and returns StrategyResponse

        Returns:
            Performance metrics

        Example:
            ```python
            def my_strategy(candle: Candle, context: Dict) -> StrategyResponse:
                # Your strategy logic here
                if should_buy:
                    return StrategyResponse.BUY
                elif should_sell:
                    return StrategyResponse.SELL
                return StrategyResponse.HOLD

            engine = SimulationEngine(config)
            metrics = await engine.run(my_strategy)
            ```
        """
        self.logger.info("Starting simulation: %s", self.config.strategy_name)
        self.logger.info("Symbol: %s, Exchange: %s", self.config.symbol, self.config.exchange)
        self.logger.info(
            "Period: %s to %s", self.config.start_date.date(), self.config.end_date.date()
        )

        try:
            # Step 1: Fetch historical data
            await self._fetch_historical_data()

            # Step 2: Run strategy on historical data
            await self._run_strategy_loop(strategy_function)

            # Step 3: Close any remaining positions
            await self._close_remaining_positions()

            # Step 4: Calculate performance metrics
            self.metrics = self._calculate_metrics()

            # Step 5: Generate reports
            if self.config.save_results:
                await self._generate_reports()

            # Step 6: Print summary
            self._print_summary()

            self.logger.info("Simulation completed successfully")

            return self.metrics

        except Exception as e:
            self.logger.error("Simulation failed: %s", e, exc_info=True)
            raise

    async def _fetch_historical_data(self) -> None:
        """Fetch historical data from exchange."""
        self.logger.info("Fetching historical data...")

        try:
            # Create exchange instance
            exchange = await ExchangeFactory.create_exchange(
                self.config.exchange, self.config.exchange_type
            )

            # Fetch historical candles
            self.historical_data = await exchange.fetch_historical_data(
                symbol=self.config.symbol,
                start_date=self.config.start_date,
                end_date=self.config.end_date,
                interval=self.config.interval,
            )

            # Close exchange connection
            await exchange.close()

            self.logger.info("Fetched %s candles", len(self.historical_data))

            if not self.historical_data:
                raise ValueError("No historical data found for the specified period")

        except Exception as e:
            self.logger.error("Failed to fetch historical data: %s", e)
            raise

    async def _run_strategy_loop(self, strategy_function: Callable) -> None:
        """
        Run strategy logic on each candle.

        Args:
            strategy_function: Strategy function to execute
        """
        self.logger.info("Running strategy loop...")

        context = {
            "portfolio": self.portfolio,
            "config": self.config,
            "candles_processed": 0,
        }

        for i, candle in enumerate(self.historical_data):
            self.current_candle_index = i
            context["candles_processed"] = i + 1
            context["current_candle"] = candle
            context["candle_index"] = i

            # Provide access to historical candles (up to current point)
            # This allows strategies to calculate indicators
            # Note: Only provide reference, don't create copy to avoid O(n²) performance
            context["candles_data"] = self.historical_data

            # Update portfolio prices
            prices = {self.config.symbol: candle.close}
            self.portfolio.update_prices(prices, candle.datetime)

            # Execute strategy
            try:
                signal = strategy_function(candle, context)

                if signal == StrategyResponse.BUY:
                    await self._handle_buy_signal(candle)
                elif signal == StrategyResponse.SELL:
                    await self._handle_sell_signal(candle)
                # HOLD - do nothing

            except Exception as e:
                self.logger.error("Error executing strategy at candle %s: %s", i, e)
                continue

            # Check risk management
            await self._check_risk_management(candle)

            # Log progress
            if (i + 1) % 1000 == 0 or i == len(self.historical_data) - 1:
                progress_pct = (i + 1) / len(self.historical_data) * 100
                self.logger.info(
                    "Progress: %s/%s candles (%.1f%%), Equity: $%.2f",
                    i + 1,
                    len(self.historical_data),
                    progress_pct,
                    self.portfolio.total_equity,
                )

    async def _handle_buy_signal(self, candle: Candle) -> None:
        """
        Handle buy signal from strategy.

        Args:
            candle: Current candle
        """
        # Check if we already have a position
        if self.portfolio.has_position(self.config.symbol):
            if not self.config.pyramid:
                return  # Can't add to position if pyramiding is disabled

            if self.portfolio.positions_count >= self.config.max_pyramiding:
                return  # Max pyramiding level reached

        # Calculate position size
        available_capital = self.portfolio.get_available_capital(self.config.position_size_pct)

        if available_capital <= 0:
            return  # No capital available

        # Apply max position size limit
        if self.config.max_position_size:
            available_capital = min(available_capital, self.config.max_position_size)

        # Calculate quantity
        price = candle.close
        commission_rate = self.config.get_effective_commission(is_maker=False)

        # Account for slippage
        effective_price = price * (1 + self.config.slippage_pct)

        # Calculate quantity (accounting for commission)
        quantity = available_capital / (effective_price * (1 + commission_rate))

        if quantity <= 0:
            return

        # Check minimum order size
        if self.config.min_order_size and quantity * effective_price < self.config.min_order_size:
            return

        # Calculate costs
        gross_cost = quantity * effective_price
        commission = gross_cost * commission_rate
        slippage_cost = quantity * price * self.config.slippage_pct

        # Execute trade
        try:
            self.portfolio.execute_trade(
                symbol=self.config.symbol,
                side=OrderSide.BUY,
                quantity=quantity,
                price=effective_price,
                timestamp=candle.datetime,
                commission=commission,
                slippage=slippage_cost,
                strategy_name=self.config.strategy_name,
                notes=f"Buy signal at {candle.datetime}",
            )

            self.logger.debug(
                "BUY %.8f @ $%.2f (commission: $%.2f)", quantity, effective_price, commission
            )

        except Exception as e:
            self.logger.error("Failed to execute buy: %s", e)

    async def _handle_sell_signal(self, candle: Candle) -> None:
        """
        Handle sell signal from strategy.

        Args:
            candle: Current candle
        """
        # Check if we have a position to sell
        if not self.portfolio.has_position(self.config.symbol):
            return

        position = self.portfolio.get_position(self.config.symbol)
        quantity = position.quantity
        price = candle.close

        # Apply slippage
        effective_price = price * (1 - self.config.slippage_pct)

        # Calculate costs
        commission_rate = self.config.get_effective_commission(is_maker=False)
        commission = quantity * effective_price * commission_rate
        slippage_cost = quantity * price * self.config.slippage_pct

        # Execute trade
        try:
            self.portfolio.execute_trade(
                symbol=self.config.symbol,
                side=OrderSide.SELL,
                quantity=quantity,
                price=effective_price,
                timestamp=candle.datetime,
                commission=commission,
                slippage=slippage_cost,
                strategy_name=self.config.strategy_name,
                notes=f"Sell signal at {candle.datetime}",
            )

            self.logger.debug(
                "SELL %.8f @ $%.2f (commission: $%.2f)", quantity, effective_price, commission
            )

        except Exception as e:
            self.logger.error("Failed to execute sell: %s", e)

    async def _check_risk_management(self, candle: Candle) -> None:
        """
        Check and enforce risk management rules.

        Args:
            candle: Current candle
        """
        if not self.portfolio.has_position(self.config.symbol):
            return

        position = self.portfolio.get_position(self.config.symbol)

        # Check stop loss
        if self.config.stop_loss_pct:
            loss_pct = ((candle.close - position.entry_price) / position.entry_price) * 100
            if loss_pct <= -self.config.stop_loss_pct:
                self.logger.info("Stop loss triggered: %.2f%%", loss_pct)
                await self._handle_sell_signal(candle)
                return

        # Check take profit
        if self.config.take_profit_pct:
            profit_pct = ((candle.close - position.entry_price) / position.entry_price) * 100
            if profit_pct >= self.config.take_profit_pct:
                self.logger.info("Take profit triggered: %.2f%%", profit_pct)
                await self._handle_sell_signal(candle)
                return

        # Check max drawdown
        if self.config.max_drawdown_pct:
            current_dd = (
                (self.portfolio.peak_equity - self.portfolio.total_equity)
                / self.portfolio.peak_equity
            ) * 100
            if current_dd >= self.config.max_drawdown_pct:
                self.logger.warning("Max drawdown exceeded: %.2f%%", current_dd)
                await self._handle_sell_signal(candle)

    async def _close_remaining_positions(self) -> None:
        """Close any remaining open positions at end of simulation."""
        if self.portfolio.positions_count > 0:
            self.logger.info("Closing %s remaining positions", self.portfolio.positions_count)

            if self.historical_data:
                last_candle = self.historical_data[-1]
                prices = {self.config.symbol: last_candle.close}
                self.portfolio.close_all_positions(prices, last_candle.datetime)

    def _calculate_metrics(self) -> PerformanceMetrics:
        """Calculate performance metrics."""
        self.logger.info("Calculating performance metrics...")

        metrics = PerformanceCalculator.calculate(
            portfolio=self.portfolio,
            start_date=self.config.start_date,
            end_date=self.config.end_date,
        )

        return metrics

    async def _generate_reports(self) -> None:
        """Generate and save performance reports."""
        self.logger.info("Generating reports...")

        try:
            report_path = PerformanceReport.save_report(
                metrics=self.metrics,
                config=self.config,
                portfolio=self.portfolio,
                output_dir=self.config.output_directory,
            )

            self.logger.info("Report saved to: %s", report_path)

            # Generate charts if enabled
            if self.config.generate_charts:
                await self._generate_charts()

        except Exception as e:
            self.logger.error("Failed to generate reports: %s", e)

    async def _generate_charts(self) -> None:
        """Generate performance charts."""
        try:
            # Create directory structure: output_dir/SYMBOL_TIMEFRAME/
            interval_str = (
                str(self.config.interval).replace("Interval.", "").replace("_", "").lower()
            )
            if hasattr(self.config.interval, "value"):
                # Map Interval enum values to strings
                interval_map = {
                    1: "1m",
                    5: "5m",
                    15: "15m",
                    30: "30m",
                    60: "1h",
                    240: "4h",
                    1440: "1d",
                }
                interval_str = interval_map.get(self.config.interval.value, "1m")

            # Create folder name with symbol, timeframe, and date range
            start_date_str = (
                self.config.start_date.strftime("%Y%m%d") if self.config.start_date else "unknown"
            )
            end_date_str = (
                self.config.end_date.strftime("%Y%m%d") if self.config.end_date else "unknown"
            )
            symbol_timeframe_dir = (
                f"{self.config.symbol}_{interval_str}_{start_date_str}_{end_date_str}"
            )
            output_path = Path(self.config.output_directory) / symbol_timeframe_dir
            output_path.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Create strategy-specific filename with params
            has_strategy_params = hasattr(self.config, "strategy_params")
            strategy_params = self.config.strategy_params if has_strategy_params else {}
            if strategy_params:
                params_str = "_".join([f"{k}_{v}" for k, v in strategy_params.items()])
                strategy_filename = f"{self.config.strategy_name}_{params_str}_{timestamp}"
            else:
                strategy_filename = f"{self.config.strategy_name}_{timestamp}"

            # Create figure with subplots
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle(
                f"{self.config.strategy_name} - {self.config.symbol}\n"
                f"{self.config.start_date.date()} to {self.config.end_date.date()}",
                fontsize=14,
                fontweight="bold",
            )

            # Equity curve
            axes[0, 0].plot(self.portfolio.equity_curve, linewidth=2, color="#2E86AB")
            axes[0, 0].axhline(
                y=self.config.initial_capital, color="gray", linestyle="--", alpha=0.5
            )
            axes[0, 0].set_title("Equity Curve")
            axes[0, 0].set_xlabel("Time")
            axes[0, 0].set_ylabel("Equity ($)")
            axes[0, 0].grid(True, alpha=0.3)
            axes[0, 0].fill_between(
                range(len(self.portfolio.equity_curve)),
                self.config.initial_capital,
                self.portfolio.equity_curve,
                alpha=0.3,
                color="green"
                if self.portfolio.equity_curve[-1] > self.config.initial_capital
                else "red",
            )

            # Returns distribution
            if len(self.portfolio.equity_curve) > 1:
                returns = [
                    (self.portfolio.equity_curve[i] - self.portfolio.equity_curve[i - 1])
                    / self.portfolio.equity_curve[i - 1]
                    * 100
                    for i in range(1, len(self.portfolio.equity_curve))
                ]
                axes[0, 1].hist(returns, bins=50, alpha=0.7, color="#A23B72", edgecolor="black")
                axes[0, 1].axvline(x=0, color="gray", linestyle="--", linewidth=2)
                axes[0, 1].set_title("Returns Distribution")
                axes[0, 1].set_xlabel("Return (%)")
                axes[0, 1].set_ylabel("Frequency")
                axes[0, 1].grid(True, alpha=0.3)

            # Performance metrics text
            metrics_text = (
                f"Total Return: {self.metrics.total_return_pct:+.2f}%\n"
                f"Annualized: {self.metrics.annualized_return_pct:+.2f}%\n"
                f"Max Drawdown: {self.metrics.max_drawdown_pct:.2f}%\n"
                f"Sharpe Ratio: {self.metrics.sharpe_ratio:.3f}\n\n"
                f"Total Trades: {self.metrics.total_trades}\n"
                f"Win Rate: {self.metrics.win_rate_pct:.1f}%\n"
                f"Profit Factor: {self.metrics.profit_factor:.2f}\n\n"
                f"Final Equity: ${self.portfolio.total_equity:,.2f}\n"
                f"Total Commission: ${self.metrics.total_commission:,.2f}"
            )
            axes[1, 0].text(
                0.1,
                0.5,
                metrics_text,
                transform=axes[1, 0].transAxes,
                fontsize=11,
                verticalalignment="center",
                family="monospace",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.3),
            )
            axes[1, 0].set_title("Performance Metrics")
            axes[1, 0].axis("off")

            # Win/Loss pie chart
            if self.metrics.total_trades > 0:
                sizes = [self.metrics.winning_trades, self.metrics.losing_trades]
                colors = ["#06D6A0", "#EF476F"]
                labels = [
                    f"Wins ({self.metrics.winning_trades})",
                    f"Losses ({self.metrics.losing_trades})",
                ]
                axes[1, 1].pie(
                    sizes, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90
                )
                axes[1, 1].set_title("Win/Loss Ratio")

            plt.tight_layout()

            # Save chart
            chart_file = output_path / f"{strategy_filename}_chart.png"
            plt.savefig(chart_file, dpi=300, bbox_inches="tight")
            plt.close()

            self.logger.info("Chart saved to: %s", chart_file)

        except Exception as e:
            self.logger.error("Failed to generate charts: %s", e)

    def _print_summary(self) -> None:
        """Print simulation summary to console."""
        if not self.config.verbose:
            return

        print("\n" + "=" * 80)
        print("SIMULATION SUMMARY".center(80))
        print("=" * 80)
        print(f"\nStrategy: {self.config.strategy_name}")
        print(f"Symbol: {self.config.symbol} | Exchange: {self.config.exchange}")
        print(f"Period: {self.config.start_date.date()} to {self.config.end_date.date()}")
        print(f"\nInitial Capital: ${self.config.initial_capital:,.2f}")
        print(f"Final Equity:    ${self.portfolio.total_equity:,.2f}")
        print(f"Total Return:    {self.metrics.total_return_pct:+.2f}%")
        print(f"Max Drawdown:    {self.metrics.max_drawdown_pct:.2f}%")
        print(f"\nTotal Trades:    {self.metrics.total_trades}")
        print(f"Win Rate:        {self.metrics.win_rate_pct:.1f}%")
        print(f"Sharpe Ratio:    {self.metrics.sharpe_ratio:.3f}")
        print("=" * 80 + "\n")

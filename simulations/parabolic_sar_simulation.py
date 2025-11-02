#!/usr/bin/env python3
"""
Parabolic SAR Strategy Simulation.

This script demonstrates a complete workflow for backtesting a Parabolic SAR trading strategy:
1. First run: Fetches data from Binance and archives it
2. Subsequent runs: Loads data from archive
3. Calculates Parabolic SAR indicators
4. Applies the trading strategy
5. Generates full performance report with charts

Usage:
    python simulations/parabolic_sar_simulation.py [--fetch] [--symbol SYMBOL] [--interval INTERVAL]

Arguments:
    --fetch: Force fetch data from Binance (even if archive exists)
    --symbol: Trading symbol (default: BTCUSDT)
    --interval: Candle interval (default: 1h for 1 hour)
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from models.data_models.candle import Candle
from models.exchange_type import ExchangeType
from models.strategy_response import StrategyResponse
from models.time_models import Interval
from modules.archive.archive_manager import ArchiveManager
from modules.strategy.technical_indicators import ExponentialMovingAverage, RelativeStrengthIndex
from scripts.binance_data_ingestor import BinanceDataIngestor
from simulations.config import SimulationConfig
from simulations.engine import SimulationEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ParabolicSARIndicator:
    """
    Parabolic SAR calculator matching TradingView implementation.

    Follows the TradingView Pine Script logic for consistency.
    """

    def __init__(self, acceleration: float = 0.02, maximum: float = 0.20):
        self.initial_acceleration = acceleration
        self.maximum_acceleration = maximum

        # State tracking
        self.is_long = True
        self.acceleration_factor = acceleration
        self.extreme_point = None
        self.current_sar = None
        self.previous_candle = None
        self.previous_candle_2 = None  # Need 2 previous candles for constraints
        self.bar_index = 0
        self.sar_values: List[float] = []
        self.next_bar_sar = None  # Store next bar SAR as per TradingView

    def calculate(self, candle: Candle) -> Optional[float]:
        """
        Calculate SAR for the given candle, matching TradingView logic.

        This follows the TradingView Pine Script implementation exactly.
        """
        # Skip first bar (bar_index 0)
        if self.bar_index == 0:
            self.previous_candle = candle
            self.bar_index += 1
            return None

        # Initialize SAR and trend on bar_index 1
        if self.bar_index == 1:
            self._initialize_trend_and_sar(candle)
            self.previous_candle = candle  # Update previous_candle for next bar
            self.bar_index += 1
            return self.current_sar

        # From bar_index 2 onwards, use next_bar_sar from previous calculation
        if self.next_bar_sar is not None:
            self.current_sar = self.next_bar_sar

        # Calculate new SAR
        new_sar = self.current_sar + self.acceleration_factor * (
            self.extreme_point - self.current_sar
        )

        # Check for reversals
        first_trend_bar = False
        if self._check_reversal(candle, new_sar):
            first_trend_bar = True
            new_sar = self._reverse_trend(candle)
        else:
            self._update_trend(candle)

        # Apply constraints as per TradingView
        if not first_trend_bar:
            new_sar = self._apply_constraints(new_sar)

        # Calculate next bar SAR
        self.next_bar_sar = new_sar + self.acceleration_factor * (self.extreme_point - new_sar)

        # Store values
        self.current_sar = new_sar
        self.previous_candle_2 = self.previous_candle
        self.previous_candle = candle
        self.sar_values.append(new_sar)
        self.bar_index += 1

        return new_sar

    def _initialize_trend_and_sar(self, candle: Candle) -> None:
        """
        Initialize trend and SAR on bar_index 1, matching TradingView logic.

        In TradingView:
        - bar_index 0: previous candle data
        - bar_index 1: determine trend and calculate first SAR
        """
        # Compare current close with previous close
        close_cur = candle.close
        close_prev = self.previous_candle.close

        if close_cur > close_prev:
            # Uptrend
            self.is_long = True
            self.extreme_point = candle.high
            prev_sar = self.previous_candle.low
            prev_ep = candle.high
        else:
            # Downtrend
            self.is_long = False
            self.extreme_point = candle.low
            prev_sar = self.previous_candle.high
            prev_ep = candle.low

        # Calculate first SAR
        self.current_sar = prev_sar + self.initial_acceleration * (prev_ep - prev_sar)
        self.next_bar_sar = self.current_sar

    def _check_reversal(self, candle: Candle, new_sar: float) -> bool:
        """Check if trend reversal occurred, matching TradingView logic."""
        if self.is_long:
            return candle.low <= new_sar
        else:
            return candle.high >= new_sar

    def _reverse_trend(self, candle: Candle) -> float:
        """Handle trend reversal, matching TradingView logic."""
        self.is_long = not self.is_long
        self.acceleration_factor = self.initial_acceleration

        if self.is_long:
            # When reversing to long: SAR = min(EP, low)
            new_sar = min(self.extreme_point, candle.low)
            self.extreme_point = candle.high
        else:
            # When reversing to short: SAR = max(EP, high)
            new_sar = max(self.extreme_point, candle.high)
            self.extreme_point = candle.low

        return new_sar

    def _update_trend(self, candle: Candle) -> None:
        """Update trend parameters."""
        if self.is_long:
            if candle.high > self.extreme_point:
                self.extreme_point = candle.high
                self.acceleration_factor = min(
                    self.acceleration_factor + self.initial_acceleration, self.maximum_acceleration
                )
        else:
            if candle.low < self.extreme_point:
                self.extreme_point = candle.low
                self.acceleration_factor = min(
                    self.acceleration_factor + self.initial_acceleration, self.maximum_acceleration
                )

    def _apply_constraints(self, sar: float) -> float:
        """Apply SAR constraints matching TradingView logic."""
        if self.previous_candle is None:
            return sar

        if self.is_long:
            # Constrain SAR to be below lows
            sar = min(sar, self.previous_candle.low)
            if self.previous_candle_2 is not None:
                sar = min(sar, self.previous_candle_2.low)
        else:
            # Constrain SAR to be above highs
            sar = max(sar, self.previous_candle.high)
            if self.previous_candle_2 is not None:
                sar = max(sar, self.previous_candle_2.high)

        return sar

    def get_trend(self) -> str:
        """Get current trend direction."""
        return "LONG" if self.is_long else "SHORT"


class ParabolicSARSimulation:
    """Manages the Parabolic SAR simulation workflow."""

    def __init__(
        self, symbol: str = "BTCUSDT", interval: str = "1h", config_file: str = "config.ini"
    ):
        self.symbol = symbol
        self.interval = interval
        self.archive_manager = ArchiveManager(config_file)
        self.data_ingestor = BinanceDataIngestor(config_file)

    async def get_or_fetch_data(
        self,
        force_fetch: bool = False,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Candle]:
        """
        Get data from archive or fetch from Binance.

        Args:
            force_fetch: Force fetch from Binance even if archive exists
            start_date: Start date for data range
            end_date: End date for data range

        Returns:
            List of candles
        """
        # Check if data exists in archive
        archive_exists = await self._check_archive_exists()

        if not force_fetch and archive_exists:
            logger.info("Loading data from archive...")
            candles = await self._load_from_archive()

            if candles:
                logger.info("Loaded %d candles from archive", len(candles))

                # Filter by date range if specified
                if start_date or end_date:
                    candles = self._filter_candles_by_date(candles, start_date, end_date)
                    logger.info("Filtered to %d candles in date range", len(candles))

                return candles
            else:
                logger.warning("Archive exists but no data found. Fetching fresh data...")

        # Fetch from Binance
        logger.info("Fetching data from Binance...")
        await self._fetch_and_save_data()

        # Load the newly saved data
        candles = await self._load_from_archive()

        if start_date or end_date:
            candles = self._filter_candles_by_date(candles, start_date, end_date)

        return candles

    async def _check_archive_exists(self) -> bool:
        """Check if archived data exists for the symbol and interval."""
        files = await self.archive_manager.get_file_names_filtered(
            exchange_code="BINANCE",
            symbol=self.symbol,
            data_type="CANDLE",
            data_frame=self.interval,
        )
        return len(files) > 0

    async def _load_from_archive(self) -> List[Candle]:
        """Load candles from archive."""
        return await self.archive_manager.read(
            exchange_code="BINANCE",
            symbol=self.symbol,
            data_type="CANDLE",
            data_frame=self.interval,
        )

    async def _fetch_and_save_data(self):
        """Fetch data from Binance and save to archive."""
        logger.info("Starting data ingestion for %s %s...", self.symbol, self.interval)
        await self.data_ingestor.ingest_monthly_data(self.symbol, self.interval)
        logger.info("Data ingestion completed and saved to archive")

    def _filter_candles_by_date(
        self, candles: List[Candle], start_date: Optional[datetime], end_date: Optional[datetime]
    ) -> List[Candle]:
        """Filter candles by date range."""
        filtered = candles

        if start_date:
            start_ts = int(start_date.timestamp() * 1000)
            filtered = [c for c in filtered if c.timestamp >= start_ts]

        if end_date:
            end_ts = int(end_date.timestamp() * 1000)
            filtered = [c for c in filtered if c.timestamp <= end_ts]

        return filtered

    async def run_simulation(
        self,
        candles: List[Candle],
        config: SimulationConfig,
        acceleration: float = 0.02,
        maximum: float = 0.20,
        use_trend_filter: bool = True,
        use_rsi_filter: bool = True,
        use_min_distance: bool = True,
        use_confirmation: bool = True,
        ema_period: int = 50,
        rsi_period: int = 14,
        rsi_overbought: float = 70.0,
        rsi_oversold: float = 30.0,
        min_distance_pct: float = 0.5,
        confirmation_candles: int = 1,
    ):
        """
        Run the Parabolic SAR strategy simulation with optional filters to improve win rate.

        Args:
            candles: Historical candles to simulate on
            config: Simulation configuration
            acceleration: Initial acceleration factor for PSAR
            maximum: Maximum acceleration factor for PSAR
            use_trend_filter: Use EMA trend filter (only trade in trend direction)
            use_rsi_filter: Use RSI momentum filter
            use_min_distance: Require minimum price distance from SAR
            use_confirmation: Wait for confirmation candles after crossover
            ema_period: Period for trend EMA filter
            rsi_period: Period for RSI calculation
            rsi_overbought: RSI level considered overbought
            rsi_oversold: RSI level considered oversold
            min_distance_pct: Minimum distance % from SAR to avoid whipsaws
            confirmation_candles: Number of candles to wait for confirmation
        """
        logger.info("Starting Parabolic SAR simulation...")
        logger.info("Strategy Parameters: acceleration=%.3f, maximum=%.3f", acceleration, maximum)
        logger.info("Filters enabled:")
        logger.info("  Trend Filter (EMA): %s (period=%d)", use_trend_filter, ema_period)
        logger.info(
            "  RSI Filter: %s (period=%d, overbought=%.1f, oversold=%.1f)",
            use_rsi_filter,
            rsi_period,
            rsi_overbought,
            rsi_oversold,
        )
        logger.info("  Min Distance Filter: %s (%.2f%%)", use_min_distance, min_distance_pct)
        logger.info("  Confirmation Delay: %s (%d candles)", use_confirmation, confirmation_candles)

        # Pre-calculate PSAR for all candles
        logger.info("Calculating Parabolic SAR indicators...")
        psar_calculator = ParabolicSARIndicator(acceleration, maximum)
        psar_values = []

        for candle in candles:
            sar = psar_calculator.calculate(candle)
            psar_values.append(sar)

        logger.info("PSAR calculation complete. Found %d values", len(psar_values))

        # Pre-calculate EMA for trend filtering (optimized batch calculation)
        ema_values = []
        if use_trend_filter:
            logger.info("Calculating EMA for trend filtering...")
            ema_indicator = ExponentialMovingAverage(period=ema_period)
            ema_values = ema_indicator.calculate_batch(candles)
            valid_ema_count = len([v for v in ema_values if v is not None])
            logger.info("EMA calculation complete: %d values", valid_ema_count)

        # Pre-calculate RSI for momentum filtering (optimized batch calculation)
        rsi_values = []
        if use_rsi_filter:
            logger.info("Calculating RSI for momentum filtering...")
            rsi_indicator = RelativeStrengthIndex(period=rsi_period)
            rsi_values = rsi_indicator.calculate_batch(candles)
            valid_rsi_count = len([v for v in rsi_values if v is not None])
            logger.info("RSI calculation complete: %d values", valid_rsi_count)

        # Track last crossover for confirmation delay
        last_crossover_index = {"buy": -1, "sell": -1}

        # Strategy function
        def parabolic_sar_strategy(candle: Candle, context: dict) -> StrategyResponse:
            """
            Improved Parabolic SAR trading strategy with multiple filters.

            Trading Rules:
            - BUY when price crosses above SAR (bullish reversal) + filters
            - SELL when price crosses below SAR (bearish reversal) + filters

            Filters applied:
            1. Trend Filter: Only trade in direction of EMA trend
            2. RSI Filter: Avoid extreme RSI levels, wait for momentum
            3. Min Distance: Require minimum separation to avoid whipsaws
            4. Confirmation: Wait N candles after crossover to confirm trend
            """
            candle_index = context["candle_index"]
            portfolio = context["portfolio"]
            has_position = portfolio.has_position(config.symbol)

            # Need at least 2 candles to detect crossover
            if candle_index < 1:
                return StrategyResponse.HOLD

            # Get current and previous SAR values
            current_sar = psar_values[candle_index]
            previous_sar = psar_values[candle_index - 1]

            # Skip if SAR values are None (first two bars)
            if current_sar is None or previous_sar is None:
                return StrategyResponse.HOLD

            # Get candles
            current_candle = candle
            previous_candle = candles[candle_index - 1]

            # Detect crossovers
            # Bullish crossover: SAR crosses below price (price was below SAR, now above)
            price_was_below_sar = previous_candle.close < previous_sar
            price_now_above_sar = current_candle.close > current_sar
            bullish_crossover = price_was_below_sar and price_now_above_sar

            # Bearish crossover: SAR crosses above price (price was above SAR, now below)
            price_was_above_sar = previous_candle.close > previous_sar
            price_now_below_sar = current_candle.close < current_sar
            bearish_crossover = price_was_above_sar and price_now_below_sar

            # Check confirmation delay
            if use_confirmation:
                # Mark crossovers when they occur
                if bullish_crossover:
                    last_crossover_index["buy"] = candle_index
                if bearish_crossover:
                    last_crossover_index["sell"] = candle_index

                # Check if enough candles have passed since last crossover
                buy_confirmed = (
                    last_crossover_index["buy"] >= 0
                    and candle_index == last_crossover_index["buy"] + confirmation_candles
                )
                sell_confirmed = (
                    last_crossover_index["sell"] >= 0
                    and candle_index == last_crossover_index["sell"] + confirmation_candles
                )

                # If crossover just happened, mark it but don't trade yet
                if bullish_crossover or bearish_crossover:
                    return StrategyResponse.HOLD
            else:
                buy_confirmed = bullish_crossover
                sell_confirmed = bearish_crossover

            # Trading logic with filters
            if buy_confirmed and not has_position:
                # Apply filters for BUY signal
                filters_passed = True

                # 1. Trend filter: Price should be above EMA (uptrend)
                if use_trend_filter and candle_index >= ema_period:
                    current_ema = ema_values[candle_index]
                    if current_ema is None or current_candle.close < current_ema:
                        filters_passed = False

                # 2. RSI filter: Avoid oversold extremes, wait for momentum recovery
                if use_rsi_filter and filters_passed and candle_index >= rsi_period:
                    current_rsi = rsi_values[candle_index]
                    if current_rsi is not None:
                        # Don't buy if extremely overbought (momentum exhausted)
                        if current_rsi > rsi_overbought:
                            filters_passed = False
                        # Prefer buying when RSI is recovering from oversold (30-50 range)
                        # This is optional - comment out if you want to allow all RSI levels
                        # if current_rsi < rsi_oversold:
                        #     filters_passed = False

                # 3. Minimum distance filter: Require minimum distance from SAR
                if use_min_distance and filters_passed:
                    distance_pct = abs((current_candle.close - current_sar) / current_sar) * 100
                    if distance_pct < min_distance_pct:
                        filters_passed = False

                if filters_passed:
                    # Reset crossover tracking
                    if use_confirmation:
                        last_crossover_index["buy"] = -1
                    return StrategyResponse.BUY

            elif sell_confirmed and has_position:
                # Apply filters for SELL signal
                filters_passed = True

                # 1. Trend filter: Price should be below EMA (downtrend)
                if use_trend_filter and candle_index >= ema_period:
                    current_ema = ema_values[candle_index]
                    if current_ema is None or current_candle.close > current_ema:
                        filters_passed = False

                # 2. RSI filter: Avoid oversold extremes, wait for momentum recovery
                if use_rsi_filter and filters_passed and candle_index >= rsi_period:
                    current_rsi = rsi_values[candle_index]
                    if current_rsi is not None:
                        # Don't sell if extremely oversold (momentum exhausted)
                        if current_rsi < rsi_oversold:
                            filters_passed = False
                        # Prefer selling when RSI is recovering from overbought (50-70 range)

                # 3. Minimum distance filter: Require minimum distance from SAR
                if use_min_distance and filters_passed:
                    distance_pct = abs((current_candle.close - current_sar) / current_sar) * 100
                    if distance_pct < min_distance_pct:
                        filters_passed = False

                if filters_passed:
                    # Reset crossover tracking
                    if use_confirmation:
                        last_crossover_index["sell"] = -1
                    return StrategyResponse.SELL

            return StrategyResponse.HOLD

        # Create modified engine that uses pre-fetched data
        engine = SimulationEngineWithData(config, candles)

        # Run simulation
        metrics = await engine.run(parabolic_sar_strategy)

        logger.info("Simulation completed successfully")

        return metrics

    async def cleanup(self):
        """Cleanup resources."""
        await self.archive_manager.shutdown()
        await self.data_ingestor.shutdown()


class SimulationEngineWithData(SimulationEngine):
    """
    Modified simulation engine that uses pre-fetched data instead of fetching.
    """

    def __init__(self, config: SimulationConfig, historical_data: List[Candle]):
        super().__init__(config)
        self.historical_data = historical_data

    async def _fetch_historical_data(self) -> None:
        """Override to use pre-provided data."""
        logger.info("Using pre-fetched data: %d candles", len(self.historical_data))

        if not self.historical_data:
            raise ValueError("No historical data provided")


def parse_interval(interval_str: str) -> Interval:
    """Parse interval string to Interval enum."""
    interval_map = {
        "1m": Interval.ONE_MINUTE,
        "5m": Interval.FIVE_MINUTES,
        "15m": Interval.FIFTEEN_MINUTES,
        "30m": Interval.THIRTY_MINUTES,
        "1h": Interval.ONE_HOUR,
        "4h": Interval.FOUR_HOURS,
        "1d": Interval.ONE_DAY,
    }
    return interval_map.get(interval_str, Interval.ONE_MINUTE)


def interval_to_string(interval: Interval) -> str:
    """Convert Interval enum to string representation."""
    interval_map = {
        Interval.ONE_MINUTE: "1m",
        Interval.FIVE_MINUTES: "5m",
        Interval.FIFTEEN_MINUTES: "15m",
        Interval.THIRTY_MINUTES: "30m",
        Interval.ONE_HOUR: "1h",
        Interval.FOUR_HOURS: "4h",
        Interval.ONE_DAY: "1d",
    }
    return interval_map.get(interval, "1m")


async def main():
    """Main function to run the Parabolic SAR simulation."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Parabolic SAR Strategy Simulation")
    parser.add_argument("--fetch", action="store_true", help="Force fetch data from Binance")
    parser.add_argument(
        "--symbol", type=str, default="BTCUSDT", help="Trading symbol (default: BTCUSDT)"
    )
    parser.add_argument("--interval", type=str, default="1h", help="Candle interval (default: 1h)")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument(
        "--capital", type=float, default=10000.0, help="Initial capital (default: 10000)"
    )
    parser.add_argument(
        "--commission", type=float, default=0.001, help="Commission rate (default: 0.001 = 0.1%%)"
    )
    parser.add_argument(
        "--slippage",
        type=float,
        default=0.0001,
        help="Slippage percentage (default: 0.0001 = 0.01%%)",
    )
    parser.add_argument(
        "--acceleration", type=float, default=0.02, help="PSAR acceleration factor (default: 0.02)"
    )
    parser.add_argument(
        "--maximum", type=float, default=0.20, help="PSAR maximum acceleration (default: 0.20)"
    )
    parser.add_argument("--stop-loss", type=float, help="Stop loss percentage (optional)")
    parser.add_argument("--take-profit", type=float, help="Take profit percentage (optional)")
    parser.add_argument("--no-trend-filter", action="store_true", help="Disable EMA trend filter")
    parser.add_argument("--no-rsi-filter", action="store_true", help="Disable RSI momentum filter")
    parser.add_argument(
        "--no-min-distance", action="store_true", help="Disable minimum distance filter"
    )
    parser.add_argument("--no-confirmation", action="store_true", help="Disable confirmation delay")
    parser.add_argument(
        "--ema-period", type=int, default=50, help="EMA period for trend filter (default: 50)"
    )
    parser.add_argument("--rsi-period", type=int, default=14, help="RSI period (default: 14)")
    parser.add_argument(
        "--rsi-overbought", type=float, default=70.0, help="RSI overbought level (default: 70.0)"
    )
    parser.add_argument(
        "--rsi-oversold", type=float, default=30.0, help="RSI oversold level (default: 30.0)"
    )
    parser.add_argument(
        "--min-distance-pct",
        type=float,
        default=0.5,
        help="Minimum distance % from SAR to avoid whipsaws (default: 0.5%%)",
    )
    parser.add_argument(
        "--confirmation-candles",
        type=int,
        default=1,
        help="Number of candles to wait for confirmation (default: 1)",
    )

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("PARABOLIC SAR STRATEGY SIMULATION".center(80))
    print("=" * 80 + "\n")

    # Parse dates
    if args.start_date:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    else:
        start_date = None  # Use all available data by default

    if args.end_date:
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    else:
        end_date = None  # Use all available data by default

    logger.info("Configuration:")
    logger.info("  Symbol: %s", args.symbol)
    logger.info("  Interval: %s", args.interval)
    if start_date and end_date:
        logger.info("  Date Range: %s to %s", start_date.date(), end_date.date())
    else:
        logger.info("  Date Range: All available data")
    logger.info("  Initial Capital: $%.2f", args.capital)
    logger.info("  Commission Rate: %.4f%% ", args.commission * 100)
    logger.info("  Slippage: %.4f%%", args.slippage * 100)
    logger.info(
        "  PSAR Parameters: acceleration=%.3f, maximum=%.3f", args.acceleration, args.maximum
    )

    # Create simulation instance
    simulation = ParabolicSARSimulation(symbol=args.symbol, interval=args.interval)

    try:
        # Step 1: Get or fetch data
        print("\n" + "-" * 80)
        print("STEP 1: DATA ACQUISITION")
        print("-" * 80)

        candles = await simulation.get_or_fetch_data(
            force_fetch=args.fetch, start_date=start_date, end_date=end_date
        )

        if not candles:
            logger.error("No data available. Exiting.")
            return

        logger.info("Data loaded successfully: %d candles", len(candles))

        # If no dates specified, use the data range
        if not start_date:
            start_date = datetime.fromtimestamp(candles[0].timestamp / 1000)
        if not end_date:
            end_date = datetime.fromtimestamp(candles[-1].timestamp / 1000)

        logger.info(
            "Date range: %s to %s",
            start_date.date(),
            end_date.date(),
        )

        # Step 2: Configure simulation
        print("\n" + "-" * 80)
        print("STEP 2: SIMULATION CONFIGURATION")
        print("-" * 80)

        config = SimulationConfig(
            symbol=args.symbol,
            exchange="BINANCE",
            exchange_type=ExchangeType.SPOT,
            interval=parse_interval(args.interval),
            start_date=start_date,
            end_date=end_date,
            initial_capital=args.capital,
            position_size_pct=0.95,  # Use 95% of capital per trade
            commission_rate=args.commission,
            slippage_pct=args.slippage,
            stop_loss_pct=args.stop_loss,
            take_profit_pct=args.take_profit,
            strategy_name=f"ParabolicSAR_{args.acceleration}_{args.maximum}",
            strategy_params={
                "acceleration": args.acceleration,
                "maximum": args.maximum,
            },
            verbose=True,
            save_results=True,
            generate_charts=True,
            output_directory="simulation_results",
        )

        logger.info("Simulation configured successfully")

        # Step 3: Run simulation
        print("\n" + "-" * 80)
        print("STEP 3: RUNNING SIMULATION")
        print("-" * 80)

        metrics = await simulation.run_simulation(
            candles=candles,
            config=config,
            acceleration=args.acceleration,
            maximum=args.maximum,
            use_trend_filter=not args.no_trend_filter,
            use_rsi_filter=not args.no_rsi_filter,
            use_min_distance=not args.no_min_distance,
            use_confirmation=not args.no_confirmation,
            ema_period=args.ema_period,
            rsi_period=args.rsi_period,
            rsi_overbought=args.rsi_overbought,
            rsi_oversold=args.rsi_oversold,
            min_distance_pct=args.min_distance_pct,
            confirmation_candles=args.confirmation_candles,
        )

        # Step 4: Display results
        print("\n" + "=" * 80)
        print("SIMULATION RESULTS".center(80))
        print("=" * 80)

        print(f"\n{'PERFORMANCE METRICS'}")
        print("-" * 80)
        print(f"Initial Capital:       ${config.initial_capital:,.2f}")
        print(f"Final Equity:          ${config.initial_capital + metrics.total_pnl:,.2f}")
        print(f"Total Return:          {metrics.total_return_pct:+.2f}%")
        print(f"Annualized Return:     {metrics.annualized_return_pct:+.2f}%")
        print(f"Max Drawdown:          {metrics.max_drawdown_pct:.2f}%")
        print(f"Sharpe Ratio:          {metrics.sharpe_ratio:.3f}")

        print(f"\n{'TRADING STATISTICS'}")
        print("-" * 80)
        print(f"Total Trades:          {metrics.total_trades}")
        print(f"Winning Trades:        {metrics.winning_trades}")
        print(f"Losing Trades:         {metrics.losing_trades}")
        print(f"Win Rate:              {metrics.win_rate_pct:.1f}%")
        print(f"Profit Factor:         {metrics.profit_factor:.2f}")
        print(f"Average Win:           ${metrics.avg_win:.2f}")
        print(f"Average Loss:          ${metrics.avg_loss:.2f}")

        print(f"\n{'COSTS'}")
        print("-" * 80)
        print(f"Total Commission:      ${metrics.total_commission:,.2f}")
        print(f"Total Slippage:        ${metrics.total_slippage:,.2f}")

        print("\n" + "=" * 80)
        print("Simulation completed! Results saved to: simulation_results/")
        print("=" * 80 + "\n")

    except Exception as e:
        logger.error("Simulation failed: %s", e, exc_info=True)
        raise
    finally:
        # Cleanup
        await simulation.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Quick Parabolic SAR Test - Simplified version for quick testing.

This is a simplified version that uses small date ranges for quick testing.
For full simulations with data fetching, use parabolic_sar_simulation.py
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from models.exchange_type import ExchangeType
from models.time_models import Interval
from simulations.config import SimulationConfig
from simulations.parabolic_sar_simulation import ParabolicSARSimulation


async def quick_test():
    """Run a quick test with minimal configuration."""

    print("\n" + "=" * 80)
    print("QUICK PARABOLIC SAR TEST".center(80))
    print("=" * 80 + "\n")

    # Configuration
    SYMBOL = "ETHUSDT"  # Change to BTCUSDT if you prefer
    INTERVAL = "1m"

    # Date range - last 7 days for quick testing
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    print(f"Testing {SYMBOL} with {INTERVAL} candles")
    print(f"Date Range: {start_date.date()} to {end_date.date()}")
    print("Note: First run will fetch data from Binance. This may take a few minutes.")
    print("Subsequent runs will load from cache.\n")

    # Create simulation
    simulation = ParabolicSARSimulation(symbol=SYMBOL, interval=INTERVAL)

    try:
        # Get data
        print("Loading data...")
        candles = await simulation.get_or_fetch_data(
            force_fetch=False,  # Set to True to force re-fetch
            start_date=start_date,
            end_date=end_date,
        )

        if not candles:
            print("No data available!")
            return

        print(f"Loaded {len(candles)} candles\n")

        # Create config
        interval_enum = Interval.ONE_MINUTE

        config = SimulationConfig(
            symbol=SYMBOL,
            exchange="BINANCE",
            exchange_type=ExchangeType.SPOT,
            interval=interval_enum,
            start_date=start_date,
            end_date=end_date,
            initial_capital=10000.0,
            position_size_pct=0.95,
            commission_rate=0.001,  # 0.1%
            slippage_pct=0.0001,  # 0.01%
            strategy_name="QuickPSAR_Test",
            verbose=True,
            save_results=True,
            generate_charts=True,
        )

        # Run simulation
        print("Running simulation...")
        metrics = await simulation.run_simulation(
            candles=candles, config=config, acceleration=0.02, maximum=0.20
        )

        # Quick summary
        print("\n" + "=" * 80)
        print("QUICK RESULTS")
        print("=" * 80)
        print(f"Return:        {metrics.total_return_pct:+.2f}%")
        print(f"Trades:        {metrics.total_trades}")
        print(f"Win Rate:      {metrics.win_rate_pct:.1f}%")
        print(f"Max Drawdown:  {metrics.max_drawdown_pct:.2f}%")
        print(f"Sharpe Ratio:  {metrics.sharpe_ratio:.3f}")
        print("=" * 80 + "\n")

    finally:
        await simulation.cleanup()


if __name__ == "__main__":
    asyncio.run(quick_test())

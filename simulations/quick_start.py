"""
Quick Start Guide for Simulation Framework.

This file provides the simplest possible examples to get started with backtesting.
"""

import asyncio
from datetime import datetime

from models.data_models.candle import Candle
from models.strategy_response import StrategyResponse
from models.time_models import Interval
from simulations.config import create_default_config
from simulations.engine import SimulationEngine

# ============================================================================
# STEP 1: Define Your Strategy
# ============================================================================


def my_first_strategy(candle: Candle, context: dict) -> StrategyResponse:
    """
    Your first strategy: Buy when price is increasing, sell when decreasing.

    Args:
        candle: Current price data (open, high, low, close, volume)
        context: Simulation state (portfolio, config, etc.)

    Returns:
        BUY, SELL, or HOLD
    """
    portfolio = context["portfolio"]
    symbol = context["config"].symbol
    has_position = portfolio.has_position(symbol)

    # Simple momentum strategy
    # Need at least 2 candles to compare
    if context["candle_index"] < 1:
        return StrategyResponse.HOLD

    # Get previous candle
    candles = context["candles_data"]
    previous_candle = candles[-2]

    # Buy if price is going up and we don't have a position
    if candle.close > previous_candle.close and not has_position:
        return StrategyResponse.BUY

    # Sell if price is going down and we have a position
    elif candle.close < previous_candle.close and has_position:
        return StrategyResponse.SELL

    return StrategyResponse.HOLD


# ============================================================================
# STEP 2: Configure and Run
# ============================================================================


async def run_my_first_backtest():
    """Run your first backtest."""

    print("\n" + "=" * 80)
    print(" WELCOME TO BACKTESTING! ".center(80, "="))
    print("=" * 80 + "\n")

    # Create configuration
    config = create_default_config(
        symbol="BTCUSDT",  # What to trade
        exchange="BINANCE",  # Where to trade
        start_date=datetime(2024, 1, 1),  # When to start
        end_date=datetime(2024, 3, 31),  # When to end
        initial_capital=10000.0,  # Starting money
        commission_rate=0.001,  # 0.1% fee
        strategy_name="MyFirstStrategy",
        interval=Interval.ONE_HOUR,  # 1-hour candles
    )

    # Create and run simulation
    engine = SimulationEngine(config)
    metrics = await engine.run(my_first_strategy)

    # Print results
    print("\n" + "=" * 80)
    print(" RESULTS ".center(80, "="))
    print("=" * 80 + "\n")
    print(f"✨ Total Return:    {metrics.total_return_pct:+.2f}%")
    print(f"💰 Final Equity:    ${metrics.total_pnl + config.initial_capital:,.2f}")
    print(f"📊 Total Trades:    {metrics.total_trades}")
    print(f"🎯 Win Rate:        {metrics.win_rate_pct:.1f}%")
    print(f"📉 Max Drawdown:    {metrics.max_drawdown_pct:.2f}%")
    print(f"⚡ Sharpe Ratio:    {metrics.sharpe_ratio:.2f}")
    print("\n" + "=" * 80 + "\n")

    return metrics


# ============================================================================
# STEP 3: Try Different Configurations
# ============================================================================


async def try_different_settings():
    """
    Try different configuration settings to see how they affect results.
    """

    print("\n" + "=" * 80)
    print(" COMPARING DIFFERENT SETTINGS ".center(80, "="))
    print("=" * 80 + "\n")

    settings = [
        {"name": "Conservative", "position_size_pct": 0.3, "stop_loss_pct": 2.0},
        {"name": "Moderate", "position_size_pct": 0.5, "stop_loss_pct": 5.0},
        {"name": "Aggressive", "position_size_pct": 1.0, "stop_loss_pct": None},
    ]

    results = []

    for setting in settings:
        config = create_default_config(
            symbol="BTCUSDT",
            exchange="BINANCE",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 3, 31),
            initial_capital=10000.0,
            position_size_pct=setting["position_size_pct"],
            stop_loss_pct=setting["stop_loss_pct"],
            strategy_name=f"Test_{setting['name']}",
            verbose=False,  # Quiet mode for comparison
        )

        engine = SimulationEngine(config)
        metrics = await engine.run(my_first_strategy)

        results.append(
            {
                "name": setting["name"],
                "return": metrics.total_return_pct,
                "trades": metrics.total_trades,
                "win_rate": metrics.win_rate_pct,
            }
        )

    # Print comparison
    print(f"{'Setting':<15} {'Return':<12} {'Trades':<10} {'Win Rate':<10}")
    print("-" * 50)
    for result in results:
        print(
            f"{result['name']:<15} "
            f"{result['return']:+8.2f}%    "
            f"{result['trades']:<10} "
            f"{result['win_rate']:6.1f}%"
        )
    print("\n" + "=" * 80 + "\n")


# ============================================================================
# STEP 4: Advanced - Using Technical Indicators
# ============================================================================


def strategy_with_sma(candle: Candle, context: dict) -> StrategyResponse:
    """
    Strategy using Simple Moving Average.

    Buy when price is above SMA.
    Sell when price is below SMA.
    """
    SMA_PERIOD = 20

    # Need enough candles
    if context["candle_index"] < SMA_PERIOD:
        return StrategyResponse.HOLD

    candles = context["candles_data"]
    portfolio = context["portfolio"]
    symbol = context["config"].symbol

    # Calculate SMA
    recent_candles = candles[-SMA_PERIOD:]
    sma = sum(c.close for c in recent_candles) / SMA_PERIOD

    has_position = portfolio.has_position(symbol)

    # Buy signal: Price crosses above SMA
    if candle.close > sma and not has_position:
        return StrategyResponse.BUY

    # Sell signal: Price crosses below SMA
    elif candle.close < sma and has_position:
        return StrategyResponse.SELL

    return StrategyResponse.HOLD


async def run_sma_strategy():
    """Run SMA strategy example."""

    print("\n" + "=" * 80)
    print(" SMA STRATEGY EXAMPLE ".center(80, "="))
    print("=" * 80 + "\n")

    config = create_default_config(
        symbol="BTCUSDT",
        exchange="BINANCE",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 6, 30),
        initial_capital=10000.0,
        strategy_name="SMA_Strategy",
        interval=Interval.FOUR_HOURS,
    )

    engine = SimulationEngine(config)
    metrics = await engine.run(strategy_with_sma)

    print(f"\n📈 Total Return: {metrics.total_return_pct:+.2f}%")
    print(f"📊 Total Trades: {metrics.total_trades}")
    print(f"🎯 Win Rate: {metrics.win_rate_pct:.1f}%\n")


# ============================================================================
# MAIN: Run Examples
# ============================================================================


async def main():
    """
    Main function - choose which example to run.

    Uncomment the example you want to try!
    """

    # 🎯 Start here: Your first backtest
    await run_my_first_backtest()

    # 🔧 Try different settings
    # await try_different_settings()

    # 📊 Advanced: SMA strategy
    # await run_sma_strategy()


if __name__ == "__main__":
    print("\n🚀 Starting Simulation Framework Quick Start...\n")
    asyncio.run(main())
    print("✅ Complete! Check the 'simulation_results' folder for detailed reports.\n")

"""
Example Simulations.

This file demonstrates how to use the simulation framework to backtest
trading strategies, similar to TradingView's strategy tester.
"""

import asyncio
from datetime import datetime

from models.data_models.candle import Candle
from models.exchange_type import ExchangeType
from models.strategy_response import StrategyResponse
from models.time_models import Interval
from simulations.config import SimulationConfig, create_default_config
from simulations.engine import SimulationEngine

# ============================================================================
# EXAMPLE 1: Simple Moving Average Crossover Strategy
# ============================================================================


async def example_sma_crossover():
    """
    Example: Simple Moving Average (SMA) crossover strategy.

    Buy when fast SMA crosses above slow SMA.
    Sell when fast SMA crosses below slow SMA.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 1: SMA Crossover Strategy")
    print("=" * 80 + "\n")

    # Create configuration
    config = create_default_config(
        symbol="BTCUSDT",
        exchange="BINANCE",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 6, 30),
        initial_capital=10000.0,
        commission_rate=0.001,  # 0.1%
        position_size_pct=0.95,  # Use 95% of capital
        strategy_name="SMA_Crossover",
        interval=Interval.ONE_HOUR,
    )

    # Strategy function
    def sma_crossover_strategy(candle: Candle, context: dict) -> StrategyResponse:
        """SMA crossover strategy logic."""
        # Parameters
        FAST_PERIOD = 10
        SLOW_PERIOD = 30

        # Need enough candles for slow SMA
        if context["candle_index"] < SLOW_PERIOD:
            return StrategyResponse.HOLD

        # Get historical candles
        portfolio = context["portfolio"]
        candles_data = context.get("candles_data", [])

        # Calculate SMAs (simplified - in production use technical indicators)
        fast_sma = _calculate_sma(candles_data, FAST_PERIOD)
        slow_sma = _calculate_sma(candles_data, SLOW_PERIOD)

        # Previous SMAs
        prev_fast_sma = _calculate_sma(candles_data[:-1], FAST_PERIOD)
        prev_slow_sma = _calculate_sma(candles_data[:-1], SLOW_PERIOD)

        # Check for crossover
        has_position = portfolio.has_position(config.symbol)

        # Bullish crossover - buy signal
        if prev_fast_sma <= prev_slow_sma and fast_sma > slow_sma:
            if not has_position:
                return StrategyResponse.BUY

        # Bearish crossover - sell signal
        elif prev_fast_sma >= prev_slow_sma and fast_sma < slow_sma:
            if has_position:
                return StrategyResponse.SELL

        return StrategyResponse.HOLD

    # Run simulation
    engine = SimulationEngine(config)
    metrics = await engine.run(sma_crossover_strategy)

    return metrics


# ============================================================================
# EXAMPLE 2: RSI Mean Reversion Strategy
# ============================================================================


async def example_rsi_strategy():
    """
    Example: RSI mean reversion strategy.

    Buy when RSI < 30 (oversold).
    Sell when RSI > 70 (overbought).
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 2: RSI Mean Reversion Strategy")
    print("=" * 80 + "\n")

    config = create_default_config(
        symbol="ETHUSDT",
        exchange="BINANCE",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 6, 30),
        initial_capital=10000.0,
        commission_rate=0.001,
        position_size_pct=0.5,  # Use 50% per trade
        strategy_name="RSI_MeanReversion",
        interval=Interval.FOUR_HOURS,
        stop_loss_pct=5.0,  # 5% stop loss
        take_profit_pct=10.0,  # 10% take profit
    )

    def rsi_strategy(candle: Candle, context: dict) -> StrategyResponse:
        """RSI mean reversion logic."""
        RSI_PERIOD = 14
        OVERSOLD = 30
        OVERBOUGHT = 70

        if context["candle_index"] < RSI_PERIOD:
            return StrategyResponse.HOLD

        # Calculate RSI (simplified)
        candles_data = context.get("candles_data", [])
        rsi = _calculate_rsi(candles_data, RSI_PERIOD)

        portfolio = context["portfolio"]
        has_position = portfolio.has_position(config.symbol)

        # Buy when oversold
        if rsi < OVERSOLD and not has_position:
            return StrategyResponse.BUY

        # Sell when overbought
        elif rsi > OVERBOUGHT and has_position:
            return StrategyResponse.SELL

        return StrategyResponse.HOLD

    engine = SimulationEngine(config)
    metrics = await engine.run(rsi_strategy)

    return metrics


# ============================================================================
# EXAMPLE 3: Buy and Hold Strategy
# ============================================================================


async def example_buy_and_hold():
    """
    Example: Simple buy and hold strategy.

    Buy on first candle, hold until end.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Buy and Hold Strategy")
    print("=" * 80 + "\n")

    config = create_default_config(
        symbol="BTCUSDT",
        exchange="BINANCE",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2024, 1, 1),
        initial_capital=10000.0,
        commission_rate=0.001,
        position_size_pct=1.0,  # Use 100% of capital
        strategy_name="BuyAndHold",
        interval=Interval.ONE_DAY,
    )

    def buy_and_hold_strategy(candle: Candle, context: dict) -> StrategyResponse:
        """Buy once and hold."""
        portfolio = context["portfolio"]

        # Buy on first candle
        if context["candle_index"] == 0:
            return StrategyResponse.BUY

        # Hold for the rest
        return StrategyResponse.HOLD

    engine = SimulationEngine(config)
    metrics = await engine.run(buy_and_hold_strategy)

    return metrics


# ============================================================================
# EXAMPLE 4: Custom Strategy with Multiple Conditions
# ============================================================================


async def example_custom_strategy():
    """
    Example: Custom strategy with multiple conditions.

    Combines trend following and momentum indicators.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Custom Multi-Condition Strategy")
    print("=" * 80 + "\n")

    config = SimulationConfig(
        symbol="BTCUSDT",
        exchange="BINANCE",
        exchange_type=ExchangeType.SPOT,
        interval=Interval.ONE_HOUR,
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 6, 30),
        initial_capital=50000.0,
        position_size_pct=0.3,  # 30% per trade
        commission_rate=0.0005,  # 0.05% (maker fee)
        slippage_pct=0.0005,  # 0.05% slippage
        stop_loss_pct=3.0,
        take_profit_pct=9.0,
        pyramid=True,  # Allow adding to positions
        max_pyramiding=3,
        strategy_name="Custom_TrendMomentum",
        verbose=True,
        save_results=True,
        generate_charts=True,
    )

    def custom_strategy(candle: Candle, context: dict) -> StrategyResponse:
        """
        Custom strategy combining multiple conditions:
        1. Price above 50-period SMA (trend)
        2. Volume above average (confirmation)
        3. Price momentum (rate of change)
        """
        if context["candle_index"] < 50:
            return StrategyResponse.HOLD

        candles_data = context.get("candles_data", [])
        portfolio = context["portfolio"]

        # Calculate indicators
        sma_50 = _calculate_sma(candles_data, 50)
        avg_volume = _calculate_avg_volume(candles_data, 20)
        momentum = _calculate_momentum(candles_data, 10)

        has_position = portfolio.has_position(config.symbol)

        # Entry conditions
        uptrend = candle.close > sma_50
        volume_spike = candle.volume > avg_volume * 1.2
        positive_momentum = momentum > 0

        if uptrend and volume_spike and positive_momentum and not has_position:
            return StrategyResponse.BUY

        # Exit conditions
        downtrend = candle.close < sma_50
        negative_momentum = momentum < 0

        if (downtrend or negative_momentum) and has_position:
            return StrategyResponse.SELL

        return StrategyResponse.HOLD

    engine = SimulationEngine(config)
    metrics = await engine.run(custom_strategy)

    return metrics


# ============================================================================
# Helper Functions (for examples only - use proper indicators in production)
# ============================================================================


def _calculate_sma(candles: list, period: int) -> float:
    """Calculate Simple Moving Average."""
    if len(candles) < period:
        return 0.0
    recent = candles[-period:]
    return sum(c.close for c in recent) / period


def _calculate_rsi(candles: list, period: int = 14) -> float:
    """Calculate Relative Strength Index (simplified)."""
    if len(candles) < period + 1:
        return 50.0

    gains = []
    losses = []

    for i in range(-period, 0):
        change = candles[i].close - candles[i - 1].close
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def _calculate_avg_volume(candles: list, period: int) -> float:
    """Calculate average volume."""
    if len(candles) < period:
        return 0.0
    recent = candles[-period:]
    return sum(c.volume for c in recent) / period


def _calculate_momentum(candles: list, period: int) -> float:
    """Calculate price momentum (rate of change)."""
    if len(candles) < period:
        return 0.0
    current_price = candles[-1].close
    past_price = candles[-period].close
    return ((current_price - past_price) / past_price) * 100


# ============================================================================
# Main Function
# ============================================================================


async def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("BACKTESTING SIMULATION EXAMPLES".center(80))
    print("=" * 80)

    # Run examples
    # Note: Uncomment the examples you want to run

    # Example 1: SMA Crossover
    # await example_sma_crossover()

    # Example 2: RSI Strategy
    # await example_rsi_strategy()

    # Example 3: Buy and Hold
    # await example_buy_and_hold()

    # Example 4: Custom Strategy
    await example_custom_strategy()

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

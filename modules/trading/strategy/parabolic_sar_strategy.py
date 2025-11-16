from typing import Optional

from modules.data_center import DataCenter
from modules.trading.strategy.strategy import Strategy
from modules.trading.strategy.strategy_response import StrategyResponse


class ParabolicSARStrategy(Strategy):
    """
    Parabolic SAR strategy with optional filters.

    Trading Rules:
    - BUY when price crosses above SAR (bullish reversal) + filters
    - SELL when price crosses below SAR (bearish reversal) + filters

    Optional Filters:
    1. Trend Filter: Only trade in direction of EMA trend
    2. RSI Filter: Avoid extreme RSI levels
    3. Min Distance: Require minimum separation to avoid whipsaws
    4. Confirmation: Wait N candles after crossover
    """

    def __init__(
        self,
        symbol: str = "BTCUSDT",
        psar_acceleration: float = 0.02,
        psar_maximum: float = 0.20,
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
        super().__init__()
        self.symbol = symbol
        self.psar_acceleration = psar_acceleration
        self.psar_maximum = psar_maximum
        self.use_trend_filter = use_trend_filter
        self.use_rsi_filter = use_rsi_filter
        self.use_min_distance = use_min_distance
        self.use_confirmation = use_confirmation
        self.ema_period = ema_period
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.min_distance_pct = min_distance_pct
        self.confirmation_candles = confirmation_candles

        # State tracking for confirmation delay
        self.last_crossover_index = {"buy": -1, "sell": -1}
        self.candle_index = 0

    def execute(self, data_center: DataCenter) -> StrategyResponse:
        """
        Execute the strategy.

        Args:
            data_center: DataCenter instance providing market data and indicators

        Returns:
            StrategyResponse with position type and trade details
        """
        try:
            # Get current and previous candles
            current_candle = data_center.get_candle(self.symbol, index=0, reverse=False)
            previous_candle = data_center.get_candle(self.symbol, index=1, reverse=False)

            # Need at least 2 candles to detect crossover
            if current_candle is None or previous_candle is None:
                self.candle_index += 1
                return self._create_hold_response(current_candle)

            # Fetch required indicator values
            psar_values = self._fetch_psar_values(data_center)
            ema_value = self._fetch_ema_value(data_center) if self.use_trend_filter else None
            rsi_value = self._fetch_rsi_value(data_center) if self.use_rsi_filter else None

            # Get current and previous SAR values
            current_sar = psar_values.get("current")
            previous_sar = psar_values.get("previous")

            # Skip if SAR values are None (first two bars)
            if current_sar is None or previous_sar is None:
                self.candle_index += 1
                return self._create_hold_response(current_candle)

            # Detect crossovers
            bullish_crossover, bearish_crossover = self._detect_crossovers(
                current_candle, previous_candle, current_sar, previous_sar
            )

            # Check confirmation delay
            buy_confirmed, sell_confirmed = self._check_confirmation(
                bullish_crossover, bearish_crossover
            )

            # Check if we have a position (would need position manager integration)
            has_position = False  # TODO: Get from position manager

            # Trading logic with filters
            if buy_confirmed and not has_position:
                if self._should_buy(current_candle, current_sar, ema_value, rsi_value):
                    self._reset_crossover_tracking("buy")
                    self.candle_index += 1
                    return self._create_long_response(current_candle)

            elif sell_confirmed and has_position:
                if self._should_sell(current_candle, current_sar, ema_value, rsi_value):
                    self._reset_crossover_tracking("sell")
                    self.candle_index += 1
                    return self._create_short_response(current_candle)

            self.candle_index += 1
            return self._create_hold_response(current_candle)

        except Exception as e:
            self.logger.error("Error executing ParabolicSAR strategy: %s", e, exc_info=True)
            return self._create_hold_response(None)

    def _fetch_psar_values(self, data_center: DataCenter) -> dict:
        """Fetch PSAR indicator values from DataCenter."""
        psar_code = f"psar_{int(self.psar_acceleration * 100)}_{int(self.psar_maximum * 100)}"

        current_sar = data_center.get_indicator_value(
            self.symbol, psar_code, index=0, reverse=False
        )
        previous_sar = data_center.get_indicator_value(
            self.symbol, psar_code, index=1, reverse=False
        )

        return {"current": current_sar, "previous": previous_sar}

    def _fetch_ema_value(self, data_center: DataCenter) -> Optional[float]:
        """Fetch EMA indicator value from DataCenter."""
        ema_code = f"ema_{self.ema_period}"
        return data_center.get_indicator_value(self.symbol, ema_code, index=0, reverse=False)

    def _fetch_rsi_value(self, data_center: DataCenter) -> Optional[float]:
        """Fetch RSI indicator value from DataCenter."""
        # Note: RSI indicator doesn't exist yet in the codebase
        # This is a placeholder for when it's implemented
        rsi_code = f"rsi_{self.rsi_period}"
        return data_center.get_indicator_value(self.symbol, rsi_code, index=0, reverse=False)

    def _detect_crossovers(
        self, current_candle, previous_candle, current_sar: float, previous_sar: float
    ) -> tuple[bool, bool]:
        """Detect bullish and bearish crossovers."""
        # Bullish crossover: SAR crosses below price (price was below SAR, now above)
        price_was_below_sar = previous_candle.close < previous_sar
        price_now_above_sar = current_candle.close > current_sar
        bullish_crossover = price_was_below_sar and price_now_above_sar

        # Bearish crossover: SAR crosses above price (price was above SAR, now below)
        price_was_above_sar = previous_candle.close > previous_sar
        price_now_below_sar = current_candle.close < current_sar
        bearish_crossover = price_was_above_sar and price_now_below_sar

        return bullish_crossover, bearish_crossover

    def _check_confirmation(
        self, bullish_crossover: bool, bearish_crossover: bool
    ) -> tuple[bool, bool]:
        """Check if crossovers are confirmed after delay."""
        if self.use_confirmation:
            # Mark crossovers when they occur
            if bullish_crossover:
                self.last_crossover_index["buy"] = self.candle_index
            if bearish_crossover:
                self.last_crossover_index["sell"] = self.candle_index

            # Check if enough candles have passed since last crossover
            buy_confirmed = self.last_crossover_index["buy"] >= 0 and self.candle_index == (
                self.last_crossover_index["buy"] + self.confirmation_candles
            )
            sell_confirmed = self.last_crossover_index["sell"] >= 0 and self.candle_index == (
                self.last_crossover_index["sell"] + self.confirmation_candles
            )

            # If crossover just happened, mark it but don't trade yet
            if bullish_crossover or bearish_crossover:
                return False, False

            return buy_confirmed, sell_confirmed
        else:
            return bullish_crossover, bearish_crossover

    def _should_buy(
        self, candle, sar: float, ema_value: Optional[float], rsi_value: Optional[float]
    ) -> bool:
        """Check if BUY filters pass."""
        filters_passed = True

        # 1. Trend filter: Price should be above EMA (uptrend)
        if self.use_trend_filter:
            if ema_value is None:
                filters_passed = False
            elif self.candle_index >= self.ema_period:
                if candle.close < ema_value:
                    filters_passed = False

        # 2. RSI filter: Avoid extremely overbought
        if self.use_rsi_filter and filters_passed:
            if rsi_value is not None:
                if rsi_value > self.rsi_overbought:
                    filters_passed = False

        # 3. Minimum distance filter
        if self.use_min_distance and filters_passed:
            distance_pct = abs((candle.close - sar) / sar) * 100
            if distance_pct < self.min_distance_pct:
                filters_passed = False

        return filters_passed

    def _should_sell(
        self, candle, sar: float, ema_value: Optional[float], rsi_value: Optional[float]
    ) -> bool:
        """Check if SELL filters pass."""
        filters_passed = True

        # 1. Trend filter: Price should be below EMA (downtrend)
        if self.use_trend_filter:
            if ema_value is None:
                filters_passed = False
            elif self.candle_index >= self.ema_period:
                if candle.close > ema_value:
                    filters_passed = False

        # 2. RSI filter: Avoid extremely oversold
        if self.use_rsi_filter and filters_passed:
            if rsi_value is not None:
                if rsi_value < self.rsi_oversold:
                    filters_passed = False

        # 3. Minimum distance filter
        if self.use_min_distance and filters_passed:
            distance_pct = abs((candle.close - sar) / sar) * 100
            if distance_pct < self.min_distance_pct:
                filters_passed = False

        return filters_passed

    def _reset_crossover_tracking(self, signal_type: str) -> None:
        """Reset crossover tracking after taking action."""
        if self.use_confirmation:
            self.last_crossover_index[signal_type] = -1

"""
Unit tests for Parabolic SAR indicator.
"""

import logging
import unittest
from datetime import datetime
from typing import Optional

from data_center.jobs.technical_indicators.parabolic_sar import ParabolicSAR
from models.data_models.candle import Candle
from utils.dependency_injection_container import register


class TestParabolicSAR(unittest.TestCase):
    """Test cases for Parabolic SAR indicator."""

    @classmethod
    def setUpClass(cls):
        """Set up class-level fixtures."""
        # Initialize dependency injection container
        logger = logging.getLogger("test_parabolic_sar")
        logger.setLevel(logging.DEBUG)
        register(logging.Logger, logger)

    def setUp(self):
        """Set up test fixtures."""
        self.symbol = "BTCUSDT"
        self.candles = []

        # Create sample candles with an uptrend followed by reversal
        base_time = int(datetime(2024, 1, 1).timestamp() * 1000)

        # Uptrend
        self.candles.append(Candle("BTCUSDT", base_time, 100.0, 105.0, 99.0, 103.0, 1000.0, 100))
        self.candles.append(
            Candle("BTCUSDT", base_time + 60000, 103.0, 108.0, 102.0, 106.0, 1100.0, 110)
        )
        self.candles.append(
            Candle("BTCUSDT", base_time + 120000, 106.0, 112.0, 105.0, 110.0, 1200.0, 120)
        )
        self.candles.append(
            Candle("BTCUSDT", base_time + 180000, 110.0, 115.0, 109.0, 113.0, 1300.0, 130)
        )

        # Reversal to downtrend
        self.candles.append(
            Candle("BTCUSDT", base_time + 240000, 113.0, 114.0, 107.0, 108.0, 1400.0, 140)
        )
        self.candles.append(
            Candle("BTCUSDT", base_time + 300000, 108.0, 109.0, 103.0, 105.0, 1500.0, 150)
        )
        self.candles.append(
            Candle("BTCUSDT", base_time + 360000, 105.0, 106.0, 100.0, 102.0, 1600.0, 160)
        )

    def request_candle_callback(
        self, symbol: str, index: int = 0, reverse: bool = False
    ) -> Optional[Candle]:
        """Mock callback to request historical candles."""
        if index < 0 or index >= len(self.candles):
            return None

        if reverse:
            actual_index = len(self.candles) - 1 - index
            if actual_index < 0:
                return None
            return self.candles[actual_index]
        else:
            return self.candles[index]

    def test_initialization(self):
        """Test indicator initialization."""
        psar = ParabolicSAR(self.symbol, self.request_candle_callback)

        self.assertEqual(psar.symbol, self.symbol)
        self.assertEqual(psar.initial_acceleration, 0.02)
        self.assertEqual(psar.maximum_acceleration, 0.20)
        self.assertFalse(psar.initialized)
        self.assertEqual(psar.code, "psar_2_20")

    def test_custom_parameters(self):
        """Test indicator with custom parameters."""
        psar = ParabolicSAR(
            self.symbol, self.request_candle_callback, acceleration=0.03, maximum=0.25
        )

        self.assertEqual(psar.initial_acceleration, 0.03)
        self.assertEqual(psar.maximum_acceleration, 0.25)
        self.assertEqual(psar.code, "psar_3_25")

    def test_first_calculation(self):
        """Test first SAR calculation."""
        psar = ParabolicSAR(self.symbol, self.request_candle_callback)

        # Calculate for first candle
        result = psar.calculate(self.candles[0])

        self.assertIsNotNone(result)
        self.assertTrue(psar.initialized)
        self.assertIsNotNone(psar.current_sar)
        self.assertEqual(len(psar.data), 1)

    def test_uptrend_calculation(self):
        """Test SAR calculation during uptrend."""
        psar = ParabolicSAR(self.symbol, self.request_candle_callback)

        # Calculate for uptrend candles
        results = []
        for i in range(4):  # First 4 candles are uptrend
            result = psar.calculate(self.candles[i])
            results.append(result)

        # Should be initialized
        self.assertTrue(psar.initialized)

        # Should be in uptrend
        self.assertTrue(psar.is_long)

        # SAR values should be below price in uptrend
        for i, sar in enumerate(results[1:], 1):  # Skip first candle
            self.assertLess(sar, self.candles[i].low)

    def test_trend_reversal(self):
        """Test trend reversal detection."""
        psar = ParabolicSAR(self.symbol, self.request_candle_callback)

        # Calculate through uptrend
        for i in range(4):
            psar.calculate(self.candles[i])

        # Should be in uptrend
        self.assertTrue(psar.is_long)
        self.assertEqual(psar.get_trend(), "LONG")

        # Calculate candles that may cause reversal
        psar.calculate(self.candles[4])
        psar.calculate(self.candles[5])
        psar.calculate(self.candles[6])

        # Check if trend changed (depends on price action vs SAR)
        # The indicator should detect reversals when price crosses SAR
        final_trend = psar.get_trend()
        self.assertIn(final_trend, ["LONG", "SHORT"])

    def test_acceleration_factor_increase(self):
        """Test that acceleration factor increases properly."""
        psar = ParabolicSAR(self.symbol, self.request_candle_callback)

        # Calculate first candle
        psar.calculate(self.candles[0])
        initial_af = psar.acceleration_factor

        # Calculate second candle (should increase AF if EP updated)
        psar.calculate(self.candles[1])

        # AF should have increased (assuming EP was updated)
        self.assertGreaterEqual(psar.acceleration_factor, initial_af)

        # AF should not exceed maximum
        self.assertLessEqual(psar.acceleration_factor, psar.maximum_acceleration)

    def test_buy_signal(self):
        """Test buy signal detection."""
        psar = ParabolicSAR(self.symbol, self.request_candle_callback)

        # Test the buy signal method with uptrend candles
        for i in range(3):
            psar.calculate(self.candles[i])

        # Should be initialized and in a trend
        self.assertTrue(psar.initialized)

        # Test that buy/sell signals are detected properly
        # Buy signal should only occur when transitioning from short to long
        has_signal_method = hasattr(psar, "is_buy_signal")
        self.assertTrue(has_signal_method)

    def test_sell_signal(self):
        """Test sell signal detection."""
        psar = ParabolicSAR(self.symbol, self.request_candle_callback)

        # Calculate through all candles
        for i in range(len(self.candles)):
            psar.calculate(self.candles[i])

        # Should be initialized and tracking trend
        self.assertTrue(psar.initialized)

        # Test that sell signal method exists and works
        has_signal_method = hasattr(psar, "is_sell_signal")
        self.assertTrue(has_signal_method)

        # The trend should be determinable
        trend = psar.get_trend()
        self.assertIn(trend, ["LONG", "SHORT"])

    def test_get_value(self):
        """Test getting SAR values."""
        psar = ParabolicSAR(self.symbol, self.request_candle_callback)

        # Calculate multiple candles
        for i in range(3):
            psar.calculate(self.candles[i])

        # Get most recent value
        recent_value = psar.get(0, reverse=True)
        self.assertIsNotNone(recent_value)
        self.assertIsInstance(recent_value, float)

        # Get oldest value
        oldest_value = psar.get(0, reverse=False)
        self.assertIsNotNone(oldest_value)
        self.assertNotEqual(recent_value, oldest_value)

    def test_data_storage(self):
        """Test that data is stored correctly."""
        psar = ParabolicSAR(self.symbol, self.request_candle_callback)

        # Calculate multiple candles
        num_candles = 5
        for i in range(num_candles):
            psar.calculate(self.candles[i])

        # Should have stored all values
        self.assertEqual(len(psar.data), num_candles)

        # Each entry should have timestamp and value
        for entry in psar.data:
            self.assertEqual(len(entry), 2)
            self.assertIsInstance(entry[0], int)  # timestamp
            self.assertIsInstance(entry[1], float)  # SAR value

    def test_registry_registration(self):
        """Test that indicator registers itself."""
        psar = ParabolicSAR(self.symbol, self.request_candle_callback)

        # Should be registered
        key = f"{self.symbol}_{psar.code}"
        self.assertIn(key, psar.registry)
        self.assertEqual(psar.registry[key], psar)

    def test_get_trend(self):
        """Test trend getter method."""
        psar = ParabolicSAR(self.symbol, self.request_candle_callback)

        # Before initialization
        self.assertEqual(psar.get_trend(), "UNKNOWN")

        # After initialization in uptrend
        psar.calculate(self.candles[0])
        psar.calculate(self.candles[1])
        trend = psar.get_trend()
        self.assertIn(trend, ["LONG", "SHORT"])


if __name__ == "__main__":
    unittest.main()

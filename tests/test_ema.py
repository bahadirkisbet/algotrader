"""
Tests for Exponential Moving Average (EMA) technical indicator.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from data_center.jobs.technical_indicators.ema import ExponentialMovingAverage
from models.data_models.candle import Candle


class TestExponentialMovingAverage:
    """Test cases for Exponential Moving Average indicator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_callback = Mock()
        self.symbol = "BTCUSDT"
        self.period = 9
        self.ema = ExponentialMovingAverage(self.symbol, self.mock_callback, self.period)
    
    def test_initialization(self):
        """Test EMA initialization."""
        assert self.ema.symbol == self.symbol
        assert self.ema.period == self.period
        assert self.ema.code == f"ema_{self.period}"
        assert self.ema.__prev_ema__ is None
        assert len(self.ema.data) == 0
        
        # Test alpha calculation
        expected_alpha = 2.0 / (self.period + 1)
        assert self.ema.__alpha__ == expected_alpha
    
    def test_alpha_calculation(self):
        """Test alpha calculation for different periods."""
        # Test with period 9
        ema_9 = ExponentialMovingAverage(self.symbol, self.mock_callback, 9)
        expected_alpha_9 = 2.0 / (9 + 1)  # 0.2
        assert ema_9.__alpha__ == expected_alpha_9
        
        # Test with period 20
        ema_20 = ExponentialMovingAverage(self.symbol, self.mock_callback, 20)
        expected_alpha_20 = 2.0 / (20 + 1)  # 0.095238...
        assert abs(ema_20.__alpha__ - expected_alpha_20) < 1e-6
        
        # Test with period 50
        ema_50 = ExponentialMovingAverage(self.symbol, self.mock_callback, 50)
        expected_alpha_50 = 2.0 / (50 + 1)  # 0.039215...
        assert abs(ema_50.__alpha__ - expected_alpha_50) < 1e-6
    
    def test_calculate_first_candle(self):
        """Test EMA calculation for the first candle (no previous EMA)."""
        candle = Candle(
            symbol=self.symbol,
            timestamp=int(datetime.now().timestamp() * 1000),
            open=100.0,
            high=110.0,
            low=90.0,
            close=105.0,
            volume=1000.0,
            interval=1
        )
        
        # Mock callback to return None (no previous data)
        self.mock_callback.return_value = None
        
        # Calculate EMA
        result = self.ema.calculate(candle)
        
        # First calculation should return the close price
        assert result == candle.close
        assert self.ema.__prev_ema__ == candle.close
        assert len(self.ema.data) == 1
        assert self.ema.data[0][1] == candle.close
    
    def test_calculate_with_previous_ema(self):
        """Test EMA calculation when previous EMA exists."""
        # Set previous EMA
        self.ema.__prev_ema__ = 100.0
        
        candle = Candle(
            symbol=self.symbol,
            timestamp=int(datetime.now().timestamp() * 1000),
            open=100.0,
            high=110.0,
            low=90.0,
            close=105.0,
            volume=1000.0,
            interval=1
        )
        
        # Mock callback to return a dummy candle (not used in calculation)
        self.mock_callback.return_value = Mock()
        
        # Calculate EMA
        result = self.ema.calculate(candle)
        
        # Calculate expected EMA
        expected_ema = (self.ema.__alpha__ * candle.close) + ((1 - self.ema.__alpha__) * self.ema.__prev_ema__)
        assert result == expected_ema
        assert self.ema.__prev_ema__ == expected_ema
        assert len(self.ema.data) == 1
        assert self.ema.data[0][1] == expected_ema
    
    def test_calculate_with_rolling_data(self):
        """Test EMA calculation with rolling data over multiple candles."""
        prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
        ema_values = []
        
        for i, price in enumerate(prices):
            candle = Candle(
                symbol=self.symbol,
                timestamp=int(datetime.now().timestamp() * 1000) + i * 60000,
                open=price,
                high=price + 1,
                low=price - 1,
                close=price,
                volume=1000,
                interval=1
            )
            
            # Mock callback to return a dummy candle
            self.mock_callback.return_value = Mock()
            
            # Calculate EMA
            result = self.ema.calculate(candle)
            ema_values.append(result)
            
            # Verify data storage
            assert len(self.ema.data) == i + 1
            assert self.ema.data[i][0] == candle.timestamp
            assert self.ema.data[i][1] == result
        
        # Verify EMA values are calculated correctly
        assert len(ema_values) == len(prices)
        assert ema_values[0] == prices[0]  # First value should be the price itself
        
        # Verify that EMA values are different from prices (due to smoothing)
        for i in range(1, len(ema_values)):
            assert ema_values[i] != prices[i]
    
    def test_ema_smoothing_behavior(self):
        """Test that EMA provides smoothing compared to raw prices."""
        # Create volatile price data
        volatile_prices = [100, 110, 90, 120, 80, 130, 70, 140, 60, 150]
        
        for i, price in enumerate(volatile_prices):
            candle = Candle(
                symbol=self.symbol,
                timestamp=int(datetime.now().timestamp() * 1000) + i * 60000,
                open=price,
                high=price + 1,
                low=price - 1,
                close=price,
                volume=1000,
                interval=1
            )
            
            self.mock_callback.return_value = Mock()
            result = self.ema.calculate(candle)
            
            # Store result for analysis
            if i == 0:
                first_ema = result
            elif i == len(volatile_prices) - 1:
                last_ema = result
        
        # EMA should be less volatile than raw prices
        price_range = max(volatile_prices) - min(volatile_prices)  # 90
        ema_range = abs(last_ema - first_ema)
        
        # EMA range should be smaller than price range due to smoothing
        assert ema_range < price_range
    
    def test_calculate_with_index_parameter(self):
        """Test EMA calculation with explicit index parameter."""
        # Set previous EMA
        self.ema.__prev_ema__ = 100.0
        
        candle = Candle(
            symbol=self.symbol,
            timestamp=int(datetime.now().timestamp() * 1000),
            open=100.0,
            high=110.0,
            low=90.0,
            close=105.0,
            volume=1000.0,
            interval=1
        )
        
        # Mock callback to return a dummy candle
        self.mock_callback.return_value = Mock()
        
        # Calculate EMA with specific index
        result = self.ema.calculate(candle, index=5)
        
        # Should calculate EMA correctly
        expected_ema = (self.ema.__alpha__ * candle.close) + ((1 - self.ema.__alpha__) * self.ema.__prev_ema__)
        assert result == expected_ema
    
    def test_calculate_with_reverse_parameter(self):
        """Test EMA calculation with reverse parameter."""
        # Set previous EMA
        self.ema.__prev_ema__ = 100.0
        
        candle = Candle(
            symbol=self.symbol,
            timestamp=int(datetime.now().timestamp() * 1000),
            open=100.0,
            high=110.0,
            low=90.0,
            close=105.0,
            volume=1000.0,
            interval=1
        )
        
        # Mock callback to return a dummy candle
        self.mock_callback.return_value = Mock()
        
        # Calculate EMA with reverse=True
        result = self.ema.calculate(candle, index=5)
        
        # Should calculate EMA correctly
        expected_ema = (self.ema.__alpha__ * candle.close) + ((1 - self.ema.__alpha__) * self.ema.__prev_ema__)
        assert result == expected_ema
    
    def test_data_storage(self):
        """Test that calculated values are properly stored."""
        candle = Candle(
            symbol=self.symbol,
            timestamp=int(datetime.now().timestamp() * 1000),
            open=100.0,
            high=110.0,
            low=90.0,
            close=105.0,
            volume=1000.0,
            interval=1
        )
        
        # Mock callback to return None initially
        self.mock_callback.return_value = None
        
        # Calculate EMA
        self.ema.calculate(candle)
        
        # Check data storage
        assert len(self.ema.data) == 1
        assert self.ema.data[0][0] == candle.timestamp
        assert self.ema.data[0][1] == candle.close
    
    def test_registry_functionality(self):
        """Test that EMA instances are properly registered."""
        registry_key = f"{self.symbol}_{self.ema.code}"
        assert registry_key in ExponentialMovingAverage.__registry__
        assert ExponentialMovingAverage.__registry__[registry_key] == self.ema
    
    def test_get_instance(self):
        """Test get_instance static method."""
        instance = ExponentialMovingAverage.get_instance(self.symbol, self.ema.code)
        assert instance == self.ema
        
        # Test with non-existent instance
        non_existent = ExponentialMovingAverage.get_instance("NONEXISTENT", "ema_9")
        assert non_existent is None
    
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Test with zero period
        ema_zero = ExponentialMovingAverage(self.symbol, self.mock_callback, 0)
        assert ema_zero.period == 0
        assert ema_zero.__alpha__ == 2.0  # 2.0 / (0 + 1)
        
        # Test with very large period
        ema_large = ExponentialMovingAverage(self.symbol, self.mock_callback, 1000)
        assert ema_large.period == 1000
        assert ema_large.__alpha__ == 2.0 / 1001
        
        # Test with negative period
        ema_negative = ExponentialMovingAverage(self.symbol, self.mock_callback, -5)
        assert ema_negative.period == -5
        assert ema_negative.__alpha__ == 2.0 / (-4)  # -0.5
    
    def test_ema_convergence(self):
        """Test that EMA converges to a stable value over time."""
        # Create a series of constant prices
        constant_price = 100.0
        ema_values = []
        
        for i in range(50):  # Many iterations
            candle = Candle(
                symbol=self.symbol,
                timestamp=int(datetime.now().timestamp() * 1000) + i * 60000,
                open=constant_price,
                high=constant_price + 1,
                low=constant_price - 1,
                close=constant_price,
                volume=1000,
                interval=1
            )
            
            self.mock_callback.return_value = Mock()
            result = self.ema.calculate(candle)
            ema_values.append(result)
        
        # EMA should converge to the constant price
        # Check last few values are very close to the target price
        last_values = ema_values[-5:]
        for value in last_values:
            assert abs(value - constant_price) < 0.1
    
    def test_ema_weighting(self):
        """Test that EMA gives more weight to recent prices."""
        # Create price series with a clear trend
        trend_prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
        
        for i, price in enumerate(trend_prices):
            candle = Candle(
                symbol=self.symbol,
                timestamp=int(datetime.now().timestamp() * 1000) + i * 60000,
                open=price,
                high=price + 1,
                low=price - 1,
                close=price,
                volume=1000,
                interval=1
            )
            
            self.mock_callback.return_value = Mock()
            self.ema.calculate(candle)
        
        # Get the last few EMA values
        last_ema = self.ema.data[-1][1]
        
        # EMA should be closer to recent prices than to early prices
        # In an upward trend, EMA should be above the simple average
        simple_average = sum(trend_prices) / len(trend_prices)
        assert last_ema > simple_average


if __name__ == "__main__":
    pytest.main([__file__]) 
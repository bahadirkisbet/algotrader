"""
Tests for Simple Moving Average (SMA) technical indicator.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from data_center.jobs.technical_indicators.sma import SimpleMovingAverage
from models.data_models.candle import Candle


class TestSimpleMovingAverage:
    """Test cases for Simple Moving Average indicator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_callback = Mock()
        self.symbol = "BTCUSDT"
        self.period = 14
        self.sma = SimpleMovingAverage(self.symbol, self.mock_callback, self.period)
    
    def test_initialization(self):
        """Test SMA initialization."""
        assert self.sma.symbol == self.symbol
        assert self.sma.period == self.period
        assert self.sma.code == f"sma_{self.period}"
        assert self.sma.__total_sum__ == 0
        assert self.sma.__total_count__ == 0
        assert len(self.sma.data) == 0
    
    def test_calculate_with_insufficient_data(self):
        """Test SMA calculation when there's insufficient historical data."""
        # Mock candle
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
        
        # Mock callback to return None (insufficient data)
        self.mock_callback.return_value = None
        
        # Calculate SMA
        result = self.sma.calculate(candle)
        
        # Should return None when insufficient data
        assert result is None
        assert self.sma.__total_count__ == 1
        assert self.sma.__total_sum__ == 105.0
        assert len(self.sma.data) == 1
        assert self.sma.data[0][1] is None
    
    def test_calculate_with_sufficient_data(self):
        """Test SMA calculation when there's sufficient historical data."""
        # Create test candles
        candles = []
        for i in range(20):  # More than period
            candle = Candle(
                symbol=self.symbol,
                timestamp=int(datetime.now().timestamp() * 1000) + i * 60000,  # 1 minute intervals
                open=100.0 + i,
                high=110.0 + i,
                low=90.0 + i,
                close=105.0 + i,
                volume=1000.0 + i,
                interval=1
            )
            candles.append(candle)
        
        # Mock callback to return historical candles
        def mock_callback(symbol, index, reverse):
            if index < len(candles):
                return candles[index]
            return None
        
        self.sma.request_callback = mock_callback
        
        # Calculate SMA for the last candle
        result = self.sma.calculate(candles[-1])
        
        # Should calculate SMA correctly
        expected_sma = sum(c.close for c in candles[-self.period:]) / self.period
        assert result == expected_sma
        assert len(self.sma.data) == 1
        assert self.sma.data[0][1] == expected_sma
    
    def test_calculate_with_rolling_window(self):
        """Test SMA calculation with rolling window behavior."""
        # Create test data
        prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113]
        candles = []
        
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
            candles.append(candle)
        
        # Mock callback
        def mock_callback(symbol, index, reverse):
            if 0 <= index < len(candles):
                return candles[index]
            return None
        
        self.sma.request_callback = mock_callback
        
        # Calculate SMA for each candle
        for i, candle in enumerate(candles):
            result = self.sma.calculate(candle)
            
            if i < self.period - 1:
                # Should return None for first period-1 candles
                assert result is None
            else:
                # Should calculate SMA for remaining candles
                expected_sma = sum(prices[i-self.period+1:i+1]) / self.period
                assert result == expected_sma
    
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
        
        # Calculate SMA
        self.sma.calculate(candle)
        
        # Check data storage
        assert len(self.sma.data) == 1
        assert self.sma.data[0][0] == candle.timestamp
        assert self.sma.data[0][1] is None  # First calculation returns None
    
    def test_registry_functionality(self):
        """Test that SMA instances are properly registered."""
        registry_key = f"{self.symbol}_{self.sma.code}"
        assert registry_key in SimpleMovingAverage.__registry__
        assert SimpleMovingAverage.__registry__[registry_key] == self.sma
    
    def test_get_instance(self):
        """Test get_instance static method."""
        instance = SimpleMovingAverage.get_instance(self.symbol, self.sma.code)
        assert instance == self.sma
        
        # Test with non-existent instance
        non_existent = SimpleMovingAverage.get_instance("NONEXISTENT", "sma_14")
        assert non_existent is None
    
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Test with zero period (should not happen in practice but good to test)
        sma_zero = SimpleMovingAverage(self.symbol, self.mock_callback, 0)
        assert sma_zero.period == 0
        
        # Test with very large period
        sma_large = SimpleMovingAverage(self.symbol, self.mock_callback, 1000)
        assert sma_large.period == 1000
        
        # Test with negative period (should not happen but good to test)
        sma_negative = SimpleMovingAverage(self.symbol, self.mock_callback, -5)
        assert sma_negative.period == -5
    
    def test_calculate_with_index_parameter(self):
        """Test SMA calculation with explicit index parameter."""
        # Create test candles
        candles = []
        for i in range(20):
            candle = Candle(
                symbol=self.symbol,
                timestamp=int(datetime.now().timestamp() * 1000) + i * 60000,
                open=100.0 + i,
                high=110.0 + i,
                low=90.0 + i,
                close=105.0 + i,
                volume=1000.0 + i,
                interval=1
            )
            candles.append(candle)
        
        # Mock callback
        def mock_callback(symbol, index, reverse):
            if 0 <= index < len(candles):
                return candles[index]
            return None
        
        self.sma.request_callback = mock_callback
        
        # Calculate SMA with specific index
        result = self.sma.calculate(candles[15], index=15)
        
        # Should calculate SMA for the specified index
        if 15 >= self.period - 1:
            expected_sma = sum(candles[15-self.period+1:16]) / self.period
            assert result == expected_sma
        else:
            assert result is None
    
    def test_calculate_with_reverse_parameter(self):
        """Test SMA calculation with reverse parameter."""
        # Create test candles
        candles = []
        for i in range(20):
            candle = Candle(
                symbol=self.symbol,
                timestamp=int(datetime.now().timestamp() * 1000) + i * 60000,
                open=100.0 + i,
                high=110.0 + i,
                low=90.0 + i,
                close=105.0 + i,
                volume=1000.0 + i,
                interval=1
            )
            candles.append(candles)
        
        # Mock callback
        def mock_callback(symbol, index, reverse):
            if reverse:
                actual_index = len(candles) - 1 - index
            else:
                actual_index = index
            
            if 0 <= actual_index < len(candles):
                return candles[actual_index]
            return None
        
        self.sma.request_callback = mock_callback
        
        # Calculate SMA with reverse=True
        result = self.sma.calculate(candles[-1], index=5)
        
        # Should calculate SMA correctly with reverse indexing
        if len(candles) - 1 - 5 >= self.period - 1:
            start_idx = len(candles) - 1 - 5 - self.period + 1
            end_idx = len(candles) - 1 - 5 + 1
            expected_sma = sum(candles[start_idx:end_idx]) / self.period
            assert result == expected_sma
        else:
            assert result is None


if __name__ == "__main__":
    pytest.main([__file__]) 
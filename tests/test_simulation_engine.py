"""
Tests for the Simulation Engine.

This module tests the backtesting simulation engine functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from pathlib import Path

from domains.backtesting.simulation_engine import (
    SimulationEngine, SimulationConfig, SimulationResult, Trade
)
from domains.strategy_engine.strategies.moving_average_crossover import MovingAverageCrossoverStrategy
from models.data_models.candle import Candle
from models.time_models import Interval


class TestSimulationConfig:
    """Test cases for SimulationConfig."""
    
    def test_initialization(self):
        """Test SimulationConfig initialization."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        config = SimulationConfig(start_date, end_date)
        
        assert config.start_date == start_date
        assert config.end_date == end_date
        assert config.initial_capital == 10000.0
        assert config.commission_rate == 0.001
        assert config.slippage == 0.0005
        assert config.data_interval == Interval.ONE_MINUTE
        assert config.enable_logging is True
        assert config.save_reports is True
        assert config.report_directory == "reports"
    
    def test_custom_parameters(self):
        """Test SimulationConfig with custom parameters."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        config = SimulationConfig(
            start_date=start_date,
            end_date=end_date,
            initial_capital=50000.0,
            commission_rate=0.002,
            slippage=0.001,
            data_interval=Interval.FIVE_MINUTES,
            enable_logging=False,
            save_reports=False,
            report_directory="custom_reports"
        )
        
        assert config.initial_capital == 50000.0
        assert config.commission_rate == 0.002
        assert config.slippage == 0.001
        assert config.data_interval == Interval.FIVE_MINUTES
        assert config.enable_logging is False
        assert config.save_reports is False
        assert config.report_directory == "custom_reports"


class TestTrade:
    """Test cases for Trade data class."""
    
    def test_trade_creation(self):
        """Test Trade object creation."""
        trade = Trade(
            trade_id="test_123",
            symbol="BTCUSDT",
            side="buy",
            quantity=1.0,
            price=50000.0,
            timestamp=datetime.now(),
            commission=25.0,
            slippage=12.5,
            total_cost=50037.5
        )
        
        assert trade.trade_id == "test_123"
        assert trade.symbol == "BTCUSDT"
        assert trade.side == "buy"
        assert trade.quantity == 1.0
        assert trade.price == 50000.0
        assert trade.commission == 25.0
        assert trade.slippage == 12.5
        assert trade.total_cost == 50037.5
    
    def test_trade_with_metadata(self):
        """Test Trade object with metadata."""
        metadata = {"strategy": "MA_Crossover", "signal_strength": "strong"}
        
        trade = Trade(
            trade_id="test_456",
            symbol="ETHUSDT",
            side="sell",
            quantity=10.0,
            price=3000.0,
            timestamp=datetime.now(),
            commission=15.0,
            slippage=7.5,
            total_cost=29977.5,
            metadata=metadata
        )
        
        assert trade.metadata == metadata


class TestSimulationResult:
    """Test cases for SimulationResult data class."""
    
    def test_simulation_result_creation(self):
        """Test SimulationResult object creation."""
        config = SimulationConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31)
        )
        
        result = SimulationResult(
            config=config,
            strategy_name="TestStrategy",
            total_trades=100,
            winning_trades=60,
            losing_trades=40,
            total_pnl=5000.0,
            total_return=50.0,
            max_drawdown=15.0,
            sharpe_ratio=1.5
        )
        
        assert result.config == config
        assert result.strategy_name == "TestStrategy"
        assert result.total_trades == 100
        assert result.winning_trades == 60
        assert result.losing_trades == 40
        assert result.total_pnl == 5000.0
        assert result.total_return == 50.0
        assert result.max_drawdown == 15.0
        assert result.sharpe_ratio == 1.5


class TestSimulationEngine:
    """Test cases for SimulationEngine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.start_date = datetime(2023, 1, 1)
        self.end_date = datetime(2023, 1, 31)
        self.config = SimulationConfig(
            start_date=self.start_date,
            end_date=self.end_date,
            initial_capital=10000.0,
            save_reports=False  # Disable reports for testing
        )
        self.engine = SimulationEngine(self.config)
    
    def test_initialization(self):
        """Test SimulationEngine initialization."""
        assert self.engine.config == self.config
        assert self.engine.current_equity == 10000.0
        assert self.engine.peak_equity == 10000.0
        assert len(self.engine.equity_curve) == 1
        assert self.engine.equity_curve[0] == 10000.0
        assert len(self.engine.trade_history) == 0
        assert self.engine.results is None
    
    def test_setup_simulation(self):
        """Test simulation setup."""
        # Test with save_reports=True
        config_with_reports = SimulationConfig(
            start_date=self.start_date,
            end_date=self.end_date,
            save_reports=True,
            report_directory="test_reports"
        )
        engine_with_reports = SimulationEngine(config_with_reports)
        
        # Check if report directory was created
        report_path = Path("test_reports")
        assert report_path.exists()
        
        # Cleanup
        import shutil
        shutil.rmtree("test_reports")
    
    def test_reset_simulation(self):
        """Test simulation state reset."""
        # Modify state
        self.engine.current_equity = 15000.0
        self.engine.peak_equity = 16000.0
        self.engine.equity_curve = [10000, 11000, 12000, 15000]
        self.engine.trade_history = [Mock(), Mock()]
        self.engine.results = Mock()
        
        # Reset
        self.engine._reset_simulation()
        
        assert self.engine.current_equity == 10000.0
        assert self.engine.peak_equity == 10000.0
        assert self.engine.equity_curve == [10000.0]
        assert len(self.engine.trade_history) == 0
        assert self.engine.results is None
    
    def test_get_all_timestamps(self):
        """Test timestamp extraction from historical data."""
        # Create test candles with different timestamps
        candles = []
        for i in range(5):
            candle = Candle(
                symbol="BTCUSDT",
                timestamp=int((self.start_date + timedelta(hours=i)).timestamp() * 1000),
                open=100.0 + i,
                high=110.0 + i,
                low=90.0 + i,
                close=105.0 + i,
                volume=1000.0 + i,
                interval=1
            )
            candles.append(candle)
        
        historical_data = {"BTCUSDT": candles}
        
        timestamps = self.engine._get_all_timestamps(historical_data)
        
        assert len(timestamps) == 5
        assert all(isinstance(ts, datetime) for ts in timestamps)
        assert timestamps[0] < timestamps[1]  # Should be sorted
    
    def test_calculate_max_drawdown(self):
        """Test maximum drawdown calculation."""
        # Test with increasing equity (no drawdown)
        self.engine.equity_curve = [10000, 11000, 12000, 13000]
        max_dd = self.engine._calculate_max_drawdown()
        assert max_dd == 0.0
        
        # Test with drawdown
        self.engine.equity_curve = [10000, 11000, 9000, 12000, 8000, 13000]
        max_dd = self.engine._calculate_max_drawdown()
        # Peak: 12000, Trough: 8000, Drawdown: (12000-8000)/12000 = 33.33%
        assert abs(max_dd - 33.33) < 0.1
    
    def test_calculate_sharpe_ratio(self):
        """Test Sharpe ratio calculation."""
        # Test with constant equity (no volatility)
        self.engine.equity_curve = [10000, 10000, 10000, 10000]
        sharpe = self.engine._calculate_sharpe_ratio()
        assert sharpe == 0.0
        
        # Test with increasing equity
        self.engine.equity_curve = [10000, 10100, 10200, 10300]
        sharpe = self.engine._calculate_sharpe_ratio()
        assert sharpe > 0  # Should be positive for increasing equity
    
    def test_is_winning_trade(self):
        """Test winning trade determination."""
        # Create a mock trade
        trade = Mock()
        trade.side = "sell"
        
        # This is a simplified test - in real implementation, you'd need to track entry/exit
        is_winning = self.engine._is_winning_trade(trade)
        assert is_winning is True
    
    @pytest.mark.asyncio
    async def test_run_simulation_integration(self):
        """Test complete simulation run integration."""
        # Create test strategy
        strategy = MovingAverageCrossoverStrategy(
            name="TestMAStrategy",
            symbols=["BTCUSDT"],
            fast_period=5,
            slow_period=10
        )
        
        # Create test historical data
        candles = []
        for i in range(20):  # Enough data for MA calculation
            candle = Candle(
                symbol="BTCUSDT",
                timestamp=int((self.start_date + timedelta(hours=i)).timestamp() * 1000),
                open=100.0 + i,
                high=110.0 + i,
                low=90.0 + i,
                close=105.0 + i,
                volume=1000.0 + i,
                interval=1
            )
            candles.append(candle)
        
        historical_data = {"BTCUSDT": candles}
        
        # Mock the exchange methods
        with patch.object(self.engine.exchange, 'connect', new_callable=AsyncMock) as mock_connect, \
             patch.object(self.engine.exchange, 'set_historical_data') as mock_set_data, \
             patch.object(self.engine.exchange, 'set_current_price') as mock_set_price:
            
            # Run simulation
            result = await self.engine.run_simulation(strategy, historical_data)
            
            # Verify results
            assert result is not None
            assert result.strategy_name == "TestMAStrategy"
            assert result.config == self.config
            assert mock_connect.called
            assert mock_set_data.called
            assert mock_set_price.called
    
    def test_create_trade_record(self):
        """Test trade record creation."""
        # Mock order response
        order_response = Mock()
        order_response.order_id = "order_123"
        order_response.symbol = "BTCUSDT"
        order_response.side = "buy"
        order_response.filled_quantity = 1.0
        order_response.average_price = 50000.0
        order_response.timestamp = datetime.now()
        
        # Mock signal
        signal = Mock()
        signal.signal_type.value = "buy"
        
        # Create trade record
        trade = self.engine._create_trade_record(order_response, signal)
        
        assert trade.trade_id == "order_123"
        assert trade.symbol == "BTCUSDT"
        assert trade.side == "buy"
        assert trade.quantity == 1.0
        assert trade.price == 50000.0
        assert trade.commission > 0
        assert trade.slippage > 0
        assert trade.total_cost > 50000.0  # Should include commission and slippage
    
    def test_update_equity(self):
        """Test equity update after trade."""
        initial_equity = self.engine.current_equity
        
        # Create a buy trade
        buy_trade = Trade(
            trade_id="test",
            symbol="BTCUSDT",
            side="buy",
            quantity=1.0,
            price=50000.0,
            timestamp=datetime.now(),
            commission=25.0,
            slippage=12.5,
            total_cost=50037.5
        )
        
        self.engine._update_equity(buy_trade)
        
        # Equity should decrease for buy trade
        assert self.engine.current_equity < initial_equity
        
        # Create a sell trade
        sell_trade = Trade(
            trade_id="test2",
            symbol="BTCUSDT",
            side="sell",
            quantity=1.0,
            price=55000.0,
            timestamp=datetime.now(),
            commission=27.5,
            slippage=13.75,
            total_cost=54958.75
        )
        
        self.engine._update_equity(sell_trade)
        
        # Equity should increase for sell trade
        assert self.engine.current_equity > initial_equity - 50037.5
    
    def test_generate_diagnostics(self):
        """Test diagnostic information generation."""
        # Set some state
        self.engine.equity_curve = [10000, 11000, 12000]
        self.engine.trade_history = [Mock(), Mock()]
        self.engine.current_equity = 12000
        self.engine.peak_equity = 12500
        
        diagnostics = self.engine._generate_diagnostics()
        
        assert diagnostics["equity_curve_length"] == 3
        assert diagnostics["trade_history_length"] == 2
        assert diagnostics["final_equity"] == 12000
        assert diagnostics["peak_equity"] == 12500
        assert diagnostics["simulation_duration"] == 30  # 31 days - 1 day = 30 days


if __name__ == "__main__":
    pytest.main([__file__]) 
"""
Unit tests for simulation framework.
"""

import unittest
from datetime import datetime

from simulations.config import SimulationConfig, create_default_config
from simulations.portfolio import OrderSide, Portfolio, Position, Trade


class TestSimulationConfig(unittest.TestCase):
    """Test simulation configuration."""

    def test_basic_config(self):
        """Test basic configuration creation."""
        config = SimulationConfig(
            symbol="BTCUSDT",
            exchange="BINANCE",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 6, 30),
        )

        self.assertEqual(config.symbol, "BTCUSDT")
        self.assertEqual(config.exchange, "BINANCE")
        self.assertEqual(config.initial_capital, 10000.0)

    def test_config_validation(self):
        """Test configuration validation."""
        # Test invalid date range
        with self.assertRaises(ValueError):
            SimulationConfig(
                symbol="BTCUSDT",
                exchange="BINANCE",
                start_date=datetime(2024, 6, 30),
                end_date=datetime(2024, 1, 1),  # End before start
            )

        # Test invalid capital
        with self.assertRaises(ValueError):
            SimulationConfig(
                symbol="BTCUSDT",
                exchange="BINANCE",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 6, 30),
                initial_capital=-1000,  # Negative
            )

    def test_create_default_config(self):
        """Test default config helper."""
        config = create_default_config(
            symbol="ETHUSDT",
            exchange="BINANCE",
        )

        self.assertEqual(config.symbol, "ETHUSDT")
        self.assertIsNotNone(config.start_date)
        self.assertIsNotNone(config.end_date)


class TestPortfolio(unittest.TestCase):
    """Test portfolio management."""

    def setUp(self):
        """Set up test portfolio."""
        self.portfolio = Portfolio(initial_capital=10000.0)

    def test_initialization(self):
        """Test portfolio initialization."""
        self.assertEqual(self.portfolio.initial_capital, 10000.0)
        self.assertEqual(self.portfolio.cash, 10000.0)
        self.assertEqual(self.portfolio.total_equity, 10000.0)
        self.assertEqual(self.portfolio.positions_count, 0)

    def test_buy_trade(self):
        """Test executing a buy trade."""
        trade = self.portfolio.execute_trade(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.1,
            price=50000.0,
            timestamp=datetime.now(),
            commission=5.0,
            strategy_name="Test",
        )

        self.assertIsNotNone(trade)
        self.assertEqual(trade.side, OrderSide.BUY)
        self.assertTrue(self.portfolio.has_position("BTCUSDT"))
        self.assertLess(self.portfolio.cash, 10000.0)

    def test_sell_trade(self):
        """Test executing a sell trade."""
        # First buy
        self.portfolio.execute_trade(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.1,
            price=50000.0,
            timestamp=datetime.now(),
            commission=5.0,
            strategy_name="Test",
        )

        # Then sell
        trade = self.portfolio.execute_trade(
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            quantity=0.1,
            price=55000.0,  # Profitable
            timestamp=datetime.now(),
            commission=5.5,
            strategy_name="Test",
        )

        self.assertIsNotNone(trade)
        self.assertEqual(trade.side, OrderSide.SELL)
        self.assertFalse(self.portfolio.has_position("BTCUSDT"))
        self.assertEqual(self.portfolio.winning_trades, 1)

    def test_insufficient_cash(self):
        """Test trade with insufficient cash."""
        with self.assertRaises(ValueError):
            self.portfolio.execute_trade(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=1.0,  # Too large
                price=50000.0,
                timestamp=datetime.now(),
                commission=0.0,
                strategy_name="Test",
            )

    def test_sell_without_position(self):
        """Test selling without position."""
        with self.assertRaises(ValueError):
            self.portfolio.execute_trade(
                symbol="BTCUSDT",
                side=OrderSide.SELL,
                quantity=0.1,
                price=50000.0,
                timestamp=datetime.now(),
                commission=0.0,
                strategy_name="Test",
            )

    def test_equity_curve(self):
        """Test equity curve tracking."""
        initial_length = len(self.portfolio.equity_curve)

        # Update prices
        self.portfolio.update_prices({"BTCUSDT": 50000.0}, datetime.now())

        # Equity curve should have grown
        self.assertGreater(len(self.portfolio.equity_curve), initial_length)

    def test_portfolio_summary(self):
        """Test portfolio summary."""
        summary = self.portfolio.get_summary()

        self.assertIn("total_equity", summary)
        self.assertIn("total_pnl", summary)
        self.assertIn("win_rate_pct", summary)
        self.assertEqual(summary["initial_capital"], 10000.0)


class TestTrade(unittest.TestCase):
    """Test trade record."""

    def test_trade_creation(self):
        """Test creating a trade record."""
        trade = Trade(
            trade_id="test-123",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.1,
            price=50000.0,
            timestamp=datetime.now(),
            commission=5.0,
            slippage=2.5,
        )

        self.assertEqual(trade.symbol, "BTCUSDT")
        self.assertEqual(trade.quantity, 0.1)
        self.assertEqual(trade.gross_value, 5000.0)
        self.assertEqual(trade.total_cost, 5007.5)

    def test_trade_to_dict(self):
        """Test trade conversion to dictionary."""
        trade = Trade(
            trade_id="test-123",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.1,
            price=50000.0,
            timestamp=datetime.now(),
        )

        trade_dict = trade.to_dict()

        self.assertIn("trade_id", trade_dict)
        self.assertIn("symbol", trade_dict)
        self.assertIn("quantity", trade_dict)


class TestPosition(unittest.TestCase):
    """Test position tracking."""

    def test_position_creation(self):
        """Test creating a position."""
        position = Position(
            symbol="BTCUSDT",
            quantity=0.1,
            entry_price=50000.0,
            entry_time=datetime.now(),
            entry_trade_id="test-123",
            current_price=50000.0,
        )

        self.assertEqual(position.symbol, "BTCUSDT")
        self.assertEqual(position.quantity, 0.1)
        self.assertEqual(position.unrealized_pnl, 0.0)

    def test_unrealized_pnl(self):
        """Test unrealized P&L calculation."""
        position = Position(
            symbol="BTCUSDT",
            quantity=0.1,
            entry_price=50000.0,
            entry_time=datetime.now(),
            entry_trade_id="test-123",
            current_price=55000.0,  # Profitable
        )

        # Should have positive unrealized P&L
        self.assertGreater(position.unrealized_pnl, 0)
        self.assertGreater(position.unrealized_pnl_pct, 0)

    def test_price_update(self):
        """Test updating position price."""
        position = Position(
            symbol="BTCUSDT",
            quantity=0.1,
            entry_price=50000.0,
            entry_time=datetime.now(),
            entry_trade_id="test-123",
            current_price=50000.0,
        )

        new_time = datetime.now()
        position.update_price(52000.0, new_time)

        self.assertEqual(position.current_price, 52000.0)
        self.assertEqual(position.last_update, new_time)


if __name__ == "__main__":
    unittest.main()

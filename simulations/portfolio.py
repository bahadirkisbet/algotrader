"""
Portfolio Management for Simulations.

This module handles position tracking, trade execution, and equity management
during backtesting.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4


class OrderSide(Enum):
    """Order side enumeration."""

    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order status enumeration."""

    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Trade:
    """
    Individual trade record.

    Represents a single executed order with all associated costs and metadata.
    """

    trade_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    timestamp: datetime

    # Costs
    commission: float = 0.0
    slippage: float = 0.0

    # Metadata
    strategy_name: str = ""
    notes: str = ""
    metadata: Dict = field(default_factory=dict)

    @property
    def total_cost(self) -> float:
        """Total cost including commission and slippage."""
        return (self.quantity * self.price) + self.commission + self.slippage

    @property
    def gross_value(self) -> float:
        """Gross value without costs."""
        return self.quantity * self.price

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "price": self.price,
            "timestamp": self.timestamp.isoformat(),
            "commission": self.commission,
            "slippage": self.slippage,
            "total_cost": self.total_cost,
            "gross_value": self.gross_value,
            "strategy_name": self.strategy_name,
            "notes": self.notes,
        }


@dataclass
class Position:
    """
    Current position in a symbol.

    Tracks the state of an open position including entry price,
    current value, and unrealized P&L.
    """

    symbol: str
    quantity: float
    entry_price: float
    entry_time: datetime
    entry_trade_id: str

    # Current state
    current_price: float = 0.0
    last_update: datetime = None

    # Costs
    total_commission: float = 0.0
    total_slippage: float = 0.0

    # Metadata
    strategy_name: str = ""
    metadata: Dict = field(default_factory=dict)

    @property
    def current_value(self) -> float:
        """Current market value of position."""
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> float:
        """Total cost basis including fees."""
        return (self.quantity * self.entry_price) + self.total_commission + self.total_slippage

    @property
    def unrealized_pnl(self) -> float:
        """Unrealized profit/loss."""
        return self.current_value - self.cost_basis

    @property
    def unrealized_pnl_pct(self) -> float:
        """Unrealized P&L as percentage."""
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100

    def update_price(self, new_price: float, timestamp: datetime) -> None:
        """Update current price and timestamp."""
        self.current_price = new_price
        self.last_update = timestamp

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time.isoformat(),
            "current_price": self.current_price,
            "current_value": self.current_value,
            "cost_basis": self.cost_basis,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_pct": self.unrealized_pnl_pct,
            "strategy_name": self.strategy_name,
        }


class Portfolio:
    """
    Portfolio manager for simulation.

    Tracks cash, positions, trades, and calculates equity and performance metrics.
    """

    def __init__(self, initial_capital: float):
        """
        Initialize portfolio.

        Args:
            initial_capital: Starting cash balance
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Trade] = []

        # Performance tracking
        self.equity_curve: List[float] = [initial_capital]
        self.equity_timestamps: List[datetime] = []
        self.peak_equity = initial_capital
        self.realized_pnl = 0.0

        # Statistics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_commission = 0.0
        self.total_slippage = 0.0

    @property
    def total_equity(self) -> float:
        """Total portfolio equity (cash + position values)."""
        positions_value = sum(pos.current_value for pos in self.positions.values())
        return self.cash + positions_value

    @property
    def unrealized_pnl(self) -> float:
        """Total unrealized P&L from open positions."""
        return sum(pos.unrealized_pnl for pos in self.positions.values())

    @property
    def total_pnl(self) -> float:
        """Total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl

    @property
    def total_return_pct(self) -> float:
        """Total return as percentage."""
        return ((self.total_equity - self.initial_capital) / self.initial_capital) * 100

    @property
    def positions_count(self) -> int:
        """Number of open positions."""
        return len(self.positions)

    def has_position(self, symbol: str) -> bool:
        """Check if position exists for symbol."""
        return symbol in self.positions

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol."""
        return self.positions.get(symbol)

    def execute_trade(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        price: float,
        timestamp: datetime,
        commission: float = 0.0,
        slippage: float = 0.0,
        strategy_name: str = "",
        notes: str = "",
    ) -> Trade:
        """
        Execute a trade and update portfolio state.

        Args:
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Trade quantity
            price: Execution price
            timestamp: Trade timestamp
            commission: Commission cost
            slippage: Slippage cost
            strategy_name: Name of strategy
            notes: Additional notes

        Returns:
            Trade object
        """
        # Create trade record
        trade = Trade(
            trade_id=str(uuid4()),
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            timestamp=timestamp,
            commission=commission,
            slippage=slippage,
            strategy_name=strategy_name,
            notes=notes,
        )

        # Update portfolio
        if side == OrderSide.BUY:
            self._execute_buy(trade)
        else:
            self._execute_sell(trade)

        # Record trade
        self.trade_history.append(trade)
        self.total_trades += 1
        self.total_commission += commission
        self.total_slippage += slippage

        return trade

    def _execute_buy(self, trade: Trade) -> None:
        """Execute buy trade."""
        # Deduct cash
        total_cost = trade.total_cost
        if total_cost > self.cash:
            raise ValueError(f"Insufficient cash: need ${total_cost:.2f}, have ${self.cash:.2f}")

        self.cash -= total_cost

        # Update or create position
        if trade.symbol in self.positions:
            # Average up existing position
            pos = self.positions[trade.symbol]
            total_quantity = pos.quantity + trade.quantity
            total_cost = pos.cost_basis + trade.total_cost
            new_avg_price = (total_cost - trade.commission - trade.slippage) / total_quantity

            pos.quantity = total_quantity
            pos.entry_price = new_avg_price
            pos.total_commission += trade.commission
            pos.total_slippage += trade.slippage
        else:
            # Open new position
            self.positions[trade.symbol] = Position(
                symbol=trade.symbol,
                quantity=trade.quantity,
                entry_price=trade.price,
                entry_time=trade.timestamp,
                entry_trade_id=trade.trade_id,
                current_price=trade.price,
                last_update=trade.timestamp,
                total_commission=trade.commission,
                total_slippage=trade.slippage,
                strategy_name=trade.strategy_name,
            )

    def _execute_sell(self, trade: Trade) -> None:
        """Execute sell trade."""
        if trade.symbol not in self.positions:
            raise ValueError(f"Cannot sell {trade.symbol}: no position exists")

        pos = self.positions[trade.symbol]

        if trade.quantity > pos.quantity:
            raise ValueError(
                f"Cannot sell {trade.quantity} of {trade.symbol}: only {pos.quantity} available"
            )

        # Calculate realized P&L
        cost_per_unit = pos.cost_basis / pos.quantity
        cost_basis = cost_per_unit * trade.quantity
        proceeds = (trade.quantity * trade.price) - trade.commission - trade.slippage
        pnl = proceeds - cost_basis

        # Update statistics
        if pnl > 0:
            self.winning_trades += 1
        elif pnl < 0:
            self.losing_trades += 1

        self.realized_pnl += pnl

        # Add proceeds to cash
        self.cash += proceeds

        # Update or close position
        if trade.quantity == pos.quantity:
            # Close entire position
            del self.positions[trade.symbol]
        else:
            # Partial close
            pos.quantity -= trade.quantity
            # Proportionally reduce commission/slippage
            ratio = trade.quantity / (pos.quantity + trade.quantity)
            pos.total_commission -= pos.total_commission * ratio
            pos.total_slippage -= pos.total_slippage * ratio

    def update_prices(self, prices: Dict[str, float], timestamp: datetime) -> None:
        """
        Update current prices for all positions.

        Args:
            prices: Dictionary of symbol -> price
            timestamp: Current timestamp
        """
        for symbol, position in self.positions.items():
            if symbol in prices:
                position.update_price(prices[symbol], timestamp)

        # Update equity curve
        current_equity = self.total_equity
        self.equity_curve.append(current_equity)
        self.equity_timestamps.append(timestamp)

        # Update peak equity
        self.peak_equity = max(self.peak_equity, current_equity)

    def get_available_capital(self, position_size_pct: float = 1.0) -> float:
        """
        Get available capital for trading.

        Args:
            position_size_pct: Percentage of equity to use

        Returns:
            Available capital amount
        """
        available = self.total_equity * position_size_pct
        return min(available, self.cash)  # Can't use more than available cash

    def close_all_positions(self, prices: Dict[str, float], timestamp: datetime) -> List[Trade]:
        """
        Close all open positions.

        Args:
            prices: Current prices for each symbol
            timestamp: Closing timestamp

        Returns:
            List of closing trades
        """
        closing_trades = []
        symbols_to_close = list(self.positions.keys())

        for symbol in symbols_to_close:
            if symbol in prices:
                pos = self.positions[symbol]
                trade = self.execute_trade(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=pos.quantity,
                    price=prices[symbol],
                    timestamp=timestamp,
                    strategy_name=pos.strategy_name,
                    notes="Position closed at end of simulation",
                )
                closing_trades.append(trade)

        return closing_trades

    def get_summary(self) -> dict:
        """Get portfolio summary statistics."""
        closed_trades = self.winning_trades + self.losing_trades
        win_rate = (self.winning_trades / closed_trades * 100) if closed_trades > 0 else 0.0

        return {
            "initial_capital": self.initial_capital,
            "cash": self.cash,
            "positions_value": self.total_equity - self.cash,
            "total_equity": self.total_equity,
            "total_pnl": self.total_pnl,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "total_return_pct": self.total_return_pct,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate_pct": win_rate,
            "total_commission": self.total_commission,
            "total_slippage": self.total_slippage,
            "open_positions": self.positions_count,
            "peak_equity": self.peak_equity,
        }

"""
Simulation engine for backtesting trading strategies.

This module provides a comprehensive backtesting environment that can
evaluate strategy performance and generate detailed reports.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from domains.trading.exchanges.simulation_exchange import SimulationExchange
from domains.strategy_engine.strategies.base_strategy import BaseStrategy
from models.data_models.candle import Candle
from models.time_models import Interval


@dataclass
class SimulationConfig:
    """Configuration for simulation runs."""
    start_date: datetime
    end_date: datetime
    initial_capital: float = 10000.0
    commission_rate: float = 0.001  # 0.1% commission
    slippage: float = 0.0005  # 0.05% slippage
    data_interval: Interval = Interval.ONE_MINUTE
    enable_logging: bool = True
    save_reports: bool = True
    report_directory: str = "reports"


@dataclass
class Trade:
    """Individual trade record."""
    trade_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    price: float
    timestamp: datetime
    commission: float
    slippage: float
    total_cost: float
    metadata: Dict = field(default_factory=dict)


@dataclass
class SimulationResult:
    """Results of a simulation run."""
    config: SimulationConfig
    strategy_name: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    timestamps: List[datetime] = field(default_factory=list)
    diagnostics: Dict = field(default_factory=dict)


class SimulationEngine:
    """
    Main simulation engine for backtesting trading strategies.
    
    This class provides a comprehensive backtesting environment that can:
    - Run strategies on historical data
    - Track performance metrics
    - Generate performance charts
    - Provide diagnostic reports
    """
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.exchange = SimulationExchange("Simulation")
        self.results: Optional[SimulationResult] = None
        
        # Performance tracking
        self.equity_curve = []
        self.trade_history = []
        self.current_equity = config.initial_capital
        self.peak_equity = config.initial_capital
        
        # Setup
        self._setup_simulation()
    
    def _setup_simulation(self) -> None:
        """Setup simulation environment."""
        # Create report directory
        if self.config.save_reports:
            Path(self.config.report_directory).mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        if self.config.enable_logging:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
    
    async def run_simulation(
        self, 
        strategy: BaseStrategy, 
        historical_data: Dict[str, List[Candle]]
    ) -> SimulationResult:
        """
        Run a complete simulation for a strategy.
        
        Args:
            strategy: Trading strategy to test
            historical_data: Historical market data by symbol
            
        Returns:
            Simulation results
        """
        self.logger.info(f"Starting simulation for strategy: {strategy.name}")
        
        # Reset simulation state
        self._reset_simulation()
        
        # Setup exchange with historical data
        await self._setup_exchange(historical_data)
        
        # Connect exchange
        await self.exchange.connect()
        
        # Run simulation loop
        await self._run_simulation_loop(strategy, historical_data)
        
        # Calculate final results
        self.results = self._calculate_results(strategy)
        
        # Generate reports
        if self.config.save_reports:
            await self._generate_reports(strategy)
        
        self.logger.info(f"Simulation completed. Total PnL: ${self.results.total_pnl:.2f}")
        
        return self.results
    
    def _reset_simulation(self) -> None:
        """Reset simulation state for new run."""
        self.equity_curve = [self.config.initial_capital]
        self.trade_history = []
        self.current_equity = self.config.initial_capital
        self.peak_equity = self.config.initial_capital
        self.results = None
    
    async def _setup_exchange(self, historical_data: Dict[str, List[Candle]) -> None:
        """Setup exchange with historical data."""
        for symbol, candles in historical_data.items():
            # Filter candles within simulation period
            filtered_candles = [
                c for c in candles 
                if self.config.start_date <= c.datetime <= self.config.end_date
            ]
            
            if filtered_candles:
                self.exchange.set_historical_data(symbol, filtered_candles)
                self.logger.info(f"Loaded {len(filtered_candles)} candles for {symbol}")
    
    async def _run_simulation_loop(
        self, 
        strategy: BaseStrategy, 
        historical_data: Dict[str, List[Candle]
    ) -> None:
        """Run the main simulation loop."""
        # Get all timestamps from historical data
        all_timestamps = self._get_all_timestamps(historical_data)
        
        for timestamp in all_timestamps:
            # Update current prices for all symbols
            await self._update_current_prices(timestamp, historical_data)
            
            # Generate strategy signals
            signals = await strategy.generate_signals(self._create_market_data_provider())
            
            # Execute signals
            for signal in signals:
                await self._execute_signal(signal, strategy)
            
            # Check exit conditions
            if await strategy.should_exit_position(self._create_market_data_provider()):
                await self._close_position(strategy)
            
            # Update equity curve
            self._update_equity_curve(timestamp)
    
    def _get_all_timestamps(self, historical_data: Dict[str, List[Candle]]) -> List[datetime]:
        """Get all unique timestamps from historical data."""
        all_timestamps = set()
        for candles in historical_data.values():
            all_timestamps.update(c.timestamp for c in candles)
        
        # Convert to datetime and sort
        timestamps = [datetime.fromtimestamp(ts / 1000) for ts in all_timestamps]
        timestamps.sort()
        
        # Filter by simulation period
        timestamps = [
            ts for ts in timestamps 
            if self.config.start_date <= ts <= self.config.end_date
        ]
        
        return timestamps
    
    async def _update_current_prices(
        self, 
        timestamp: datetime, 
        historical_data: Dict[str, List[Candle]]
    ) -> None:
        """Update current prices for all symbols at given timestamp."""
        for symbol, candles in historical_data.items():
            # Find candle at or before timestamp
            current_candle = None
            for candle in reversed(candles):
                if candle.datetime <= timestamp:
                    current_candle = candle
                    break
            
            if current_candle:
                self.exchange.set_current_price(symbol, current_candle.close)
    
    def _create_market_data_provider(self):
        """Create a market data provider for the strategy."""
        # This would implement the MarketDataProvider protocol
        # For now, return a simple implementation
        return SimpleMarketDataProvider(self.exchange)
    
    async def _execute_signal(self, signal: Any, strategy: BaseStrategy) -> None:
        """Execute a trading signal."""
        try:
            # Calculate position size
            position_size = strategy.calculate_position_size(
                self.current_equity,
                strategy.get_parameter("position_size_pct", 0.1)
            )
            
            if position_size <= 0:
                return
            
            # Create order request
            order_request = strategy.create_order_request(signal, position_size)
            
            # Place order
            order_response = await self.exchange.place_order(order_request)
            
            if order_response.status == "filled":
                # Record trade
                trade = self._create_trade_record(order_response, signal)
                self.trade_history.append(trade)
                
                # Update equity
                self._update_equity(trade)
                
                self.logger.info(f"Executed {signal.signal_type.value} order for {signal.symbol}")
        
        except Exception as e:
            self.logger.error(f"Error executing signal: {e}")
    
    def _create_trade_record(self, order_response: Any, signal: Any) -> Trade:
        """Create a trade record from order response."""
        # Calculate costs
        commission = order_response.filled_quantity * order_response.average_price * self.config.commission_rate
        slippage = order_response.filled_quantity * order_response.average_price * self.config.slippage
        total_cost = (order_response.filled_quantity * order_response.average_price) + commission + slippage
        
        return Trade(
            trade_id=order_response.order_id,
            symbol=order_response.symbol,
            side=order_response.side,
            quantity=order_response.filled_quantity,
            price=order_response.average_price,
            timestamp=order_response.timestamp,
            commission=commission,
            slippage=slippage,
            total_cost=total_cost,
            metadata={"signal_type": str(signal.signal_type)}
        )
    
    def _update_equity(self, trade: Trade) -> None:
        """Update equity after trade execution."""
        if trade.side == "buy":
            self.current_equity -= trade.total_cost
        else:  # sell
            self.current_equity += (trade.quantity * trade.price) - trade.commission - trade.slippage
        
        # Update peak equity
        self.peak_equity = max(self.peak_equity, self.current_equity)
    
    async def _close_position(self, strategy: BaseStrategy) -> None:
        """Close current position."""
        # Implementation would depend on strategy state
        # For now, just log the action
        self.logger.info("Closing position based on strategy exit condition")
    
    def _update_equity_curve(self, timestamp: datetime) -> None:
        """Update equity curve with current value."""
        self.equity_curve.append(self.current_equity)
    
    def _calculate_results(self, strategy: BaseStrategy) -> SimulationResult:
        """Calculate final simulation results."""
        # Calculate basic metrics
        total_trades = len(self.trade_history)
        winning_trades = len([t for t in self.trade_history if self._is_winning_trade(t)])
        losing_trades = total_trades - winning_trades
        
        total_pnl = self.current_equity - self.config.initial_capital
        total_return = (total_pnl / self.config.initial_capital) * 100
        
        # Calculate max drawdown
        max_drawdown = self._calculate_max_drawdown()
        
        # Calculate Sharpe ratio (simplified)
        sharpe_ratio = self._calculate_sharpe_ratio()
        
        # Create result object
        result = SimulationResult(
            config=self.config,
            strategy_name=strategy.name,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            total_pnl=total_pnl,
            total_return=total_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            trades=self.trade_history.copy(),
            equity_curve=self.equity_curve.copy(),
            timestamps=[],  # Would be populated with actual timestamps
            diagnostics=self._generate_diagnostics()
        )
        
        return result
    
    def _is_winning_trade(self, trade: Trade) -> bool:
        """Determine if a trade was profitable."""
        # This is a simplified implementation
        # In a real system, you'd track entry and exit prices
        return trade.side == "sell"  # Simplified assumption
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from peak equity."""
        if not self.equity_curve:
            return 0.0
        
        max_drawdown = 0.0
        peak = self.equity_curve[0]
        
        for equity in self.equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown * 100  # Return as percentage
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio (simplified)."""
        if len(self.equity_curve) < 2:
            return 0.0
        
        # Calculate returns
        returns = []
        for i in range(1, len(self.equity_curve)):
            ret = (self.equity_curve[i] - self.equity_curve[i-1]) / self.equity_curve[i-1]
            returns.append(ret)
        
        if not returns:
            return 0.0
        
        # Calculate Sharpe ratio (assuming 0% risk-free rate)
        avg_return = sum(returns) / len(returns)
        std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
        
        if std_return == 0:
            return 0.0
        
        # Annualize (assuming daily data)
        sharpe = (avg_return / std_return) * (252 ** 0.5)
        return sharpe
    
    def _generate_diagnostics(self) -> Dict:
        """Generate diagnostic information."""
        return {
            "equity_curve_length": len(self.equity_curve),
            "trade_history_length": len(self.trade_history),
            "final_equity": self.current_equity,
            "peak_equity": self.peak_equity,
            "simulation_duration": (self.config.end_date - self.config.start_date).days,
            "exchange_state": self.exchange.get_simulation_state()
        }
    
    async def _generate_reports(self, strategy: BaseStrategy) -> None:
        """Generate and save simulation reports."""
        if not self.results:
            return
        
        # Generate performance charts
        await self._generate_performance_charts()
        
        # Generate diagnostic report
        await self._generate_diagnostic_report(strategy)
        
        # Save results to file
        await self._save_results_to_file()
    
    async def _generate_performance_charts(self) -> None:
        """Generate performance visualization charts."""
        try:
            # Set style
            plt.style.use('seaborn-v0_8')
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle(f'Strategy Performance: {self.results.strategy_name}', fontsize=16)
            
            # Equity curve
            axes[0, 0].plot(self.equity_curve, linewidth=2, color='blue')
            axes[0, 0].set_title('Equity Curve')
            axes[0, 0].set_xlabel('Time')
            axes[0, 0].set_ylabel('Equity ($)')
            axes[0, 0].grid(True, alpha=0.3)
            
            # Trade distribution
            if self.trade_history:
                trade_pnls = [t.total_cost for t in self.trade_history]
                axes[0, 1].hist(trade_pnls, bins=20, alpha=0.7, color='green')
                axes[0, 1].set_title('Trade Distribution')
                axes[0, 1].set_xlabel('Trade PnL ($)')
                axes[0, 1].set_ylabel('Frequency')
                axes[0, 1].grid(True, alpha=0.3)
            
            # Performance metrics
            metrics_text = f"""
            Total Return: {self.results.total_return:.2f}%
            Total PnL: ${self.results.total_pnl:.2f}
            Max Drawdown: {self.results.max_drawdown:.2f}%
            Sharpe Ratio: {self.results.sharpe_ratio:.2f}
            Total Trades: {self.results.total_trades}
            Win Rate: {(self.results.winning_trades/self.results.total_trades*100):.1f}%
            """
            axes[1, 0].text(0.1, 0.5, metrics_text, transform=axes[1, 0].transAxes, 
                           fontsize=12, verticalalignment='center')
            axes[1, 0].set_title('Performance Metrics')
            axes[1, 0].axis('off')
            
            # Win/Loss ratio
            if self.results.total_trades > 0:
                win_rate = self.results.winning_trades / self.results.total_trades
                loss_rate = 1 - win_rate
                axes[1, 1].pie([win_rate, loss_rate], labels=['Wins', 'Losses'], 
                              autopct='%1.1f%%', colors=['green', 'red'])
                axes[1, 1].set_title('Win/Loss Ratio')
            
            plt.tight_layout()
            
            # Save chart
            chart_path = Path(self.config.report_directory) / f"{self.results.strategy_name}_performance.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Performance charts saved to {chart_path}")
        
        except Exception as e:
            self.logger.error(f"Error generating performance charts: {e}")
    
    async def _generate_diagnostic_report(self, strategy: BaseStrategy) -> None:
        """Generate diagnostic report identifying potential issues."""
        diagnostics = []
        
        # Check for common issues
        if self.results.total_trades == 0:
            diagnostics.append("WARNING: No trades executed during simulation")
        
        if self.results.max_drawdown > 50:
            diagnostics.append(f"WARNING: High maximum drawdown: {self.results.max_drawdown:.2f}%")
        
        if self.results.sharpe_ratio < 0:
            diagnostics.append(f"WARNING: Negative Sharpe ratio: {self.results.sharpe_ratio:.2f}")
        
        if len(self.equity_curve) < 100:
            diagnostics.append("INFO: Limited data points for analysis")
        
        # Strategy-specific diagnostics
        strategy_info = strategy.get_performance_summary()
        if strategy_info.get("total_signals", 0) == 0:
            diagnostics.append("WARNING: Strategy generated no signals")
        
        # Save diagnostic report
        report_path = Path(self.config.report_directory) / f"{self.results.strategy_name}_diagnostics.txt"
        with open(report_path, 'w') as f:
            f.write(f"Diagnostic Report for {self.results.strategy_name}\n")
            f.write("=" * 50 + "\n\n")
            
            for diagnostic in diagnostics:
                f.write(f"{diagnostic}\n")
            
            f.write(f"\nStrategy State:\n")
            f.write(f"Active: {strategy.state.is_active}\n")
            f.write(f"Current Position: {strategy.state.current_position}\n")
            f.write(f"Entry Price: {strategy.state.entry_price}\n")
            
            f.write(f"\nSimulation Diagnostics:\n")
            for key, value in self.results.diagnostics.items():
                f.write(f"{key}: {value}\n")
        
        self.logger.info(f"Diagnostic report saved to {report_path}")
    
    async def _save_results_to_file(self) -> None:
        """Save simulation results to file."""
        try:
            results_path = Path(self.config.report_directory) / f"{self.results.strategy_name}_results.json"
            
            # Convert results to JSON-serializable format
            results_dict = {
                "strategy_name": self.results.strategy_name,
                "total_trades": self.results.total_trades,
                "winning_trades": self.results.winning_trades,
                "losing_trades": self.results.losing_trades,
                "total_pnl": self.results.total_pnl,
                "total_return": self.results.total_return,
                "max_drawdown": self.results.max_drawdown,
                "sharpe_ratio": self.results.sharpe_ratio,
                "final_equity": self.current_equity,
                "initial_capital": self.config.initial_capital
            }
            
            import json
            with open(results_path, 'w') as f:
                json.dump(results_dict, f, indent=2, default=str)
            
            self.logger.info(f"Results saved to {results_path}")
        
        except Exception as e:
            self.logger.error(f"Error saving results: {e}")


class SimpleMarketDataProvider:
    """Simple market data provider for simulation."""
    
    def __init__(self, exchange: SimulationExchange):
        self.exchange = exchange
    
    async def get_latest_candle(self, symbol: str):
        """Get latest candle for symbol."""
        # Implementation would get latest candle from exchange
        pass
    
    async def get_historical_data(self, symbol: str, start_time, end_time, limit=None):
        """Get historical data for symbol."""
        return await self.exchange.get_historical_data(
            symbol, None, start_time, end_time, limit
        )
    
    async def get_indicator_value(self, symbol: str, indicator_name: str):
        """Get indicator value."""
        # Implementation would calculate or retrieve indicator values
        pass 
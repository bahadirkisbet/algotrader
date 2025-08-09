"""
Simulation exchange for backtesting strategies.

This module provides a simulation environment that mimics real exchange
behavior without requiring actual API connections.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

from .base_exchange import BaseExchange, OrderRequest, OrderResponse, Position
from models.data_models.candle import Candle
from models.time_models import Interval


@dataclass
class SimulationOrder:
    """Internal order representation for simulation."""
    order_id: str
    request: OrderRequest
    status: str  # 'pending', 'filled', 'cancelled'
    created_at: datetime
    filled_at: Optional[datetime] = None
    filled_quantity: float = 0.0
    average_price: Optional[float] = None


class SimulationExchange(BaseExchange):
    """
    Simulation exchange for backtesting strategies.
    
    This class provides a realistic simulation of exchange behavior
    including order matching, position tracking, and market data.
    """
    
    def __init__(self, name: str = "Simulation"):
        super().__init__(name, is_simulation=True)
        self._orders: Dict[str, SimulationOrder] = {}
        self._positions: Dict[str, Position] = {}
        self._balance: Dict[str, float] = {"USDT": 10000.0}  # Default starting balance
        self._historical_data: Dict[str, List[Candle]] = {}
        self._current_prices: Dict[str, float] = {}
        self._order_counter = 0
        
    async def connect(self) -> bool:
        """Simulate connection to exchange."""
        await asyncio.sleep(0.1)  # Simulate connection delay
        self.connected = True
        return True
    
    async def disconnect(self) -> None:
        """Simulate disconnection from exchange."""
        self.connected = False
    
    async def get_account_info(self) -> Dict:
        """Get simulated account information."""
        total_balance = sum(self._balance.values())
        return {
            "total_balance": total_balance,
            "balances": self._balance.copy(),
            "positions": len(self._positions)
        }
    
    async def get_symbols(self) -> List[str]:
        """Get available trading symbols from historical data."""
        return list(self._historical_data.keys())
    
    async def get_historical_data(
        self, 
        symbol: str, 
        interval: Interval, 
        start_time: datetime, 
        end_time: datetime,
        limit: Optional[int] = None
    ) -> List[Candle]:
        """Get historical market data for simulation."""
        if symbol not in self._historical_data:
            return []
        
        candles = self._historical_data[symbol]
        
        # Filter by time range
        filtered_candles = [
            c for c in candles 
            if start_time <= c.datetime <= end_time
        ]
        
        if limit:
            filtered_candles = filtered_candles[-limit:]
        
        return filtered_candles
    
    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Place a simulated order."""
        if not self.connected:
            raise RuntimeError("Exchange not connected")
        
        # Generate unique order ID
        order_id = f"sim_{uuid.uuid4().hex[:8]}"
        
        # Create simulation order
        sim_order = SimulationOrder(
            order_id=order_id,
            request=order_request,
            status="pending",
            created_at=datetime.now()
        )
        
        self._orders[order_id] = sim_order
        
        # Simulate order processing
        await self._process_order(sim_order)
        
        # Create response
        response = OrderResponse(
            order_id=order_id,
            symbol=order_request.symbol,
            side=order_request.side,
            order_type=order_request.order_type,
            quantity=order_request.quantity,
            price=order_request.price,
            status=sim_order.status,
            timestamp=sim_order.created_at,
            filled_quantity=sim_order.filled_quantity,
            average_price=sim_order.average_price
        )
        
        return response
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel a simulated order."""
        if order_id not in self._orders:
            return False
        
        order = self._orders[order_id]
        if order.status == "pending":
            order.status = "cancelled"
            return True
        
        return False
    
    async def get_order_status(self, order_id: str, symbol: str) -> OrderResponse:
        """Get the status of a simulated order."""
        if order_id not in self._orders:
            raise ValueError(f"Order {order_id} not found")
        
        order = self._orders[order_id]
        return OrderResponse(
            order_id=order.order_id,
            symbol=order.request.symbol,
            side=order.request.side,
            order_type=order.request.order_type,
            quantity=order.request.quantity,
            price=order.request.price,
            status=order.status,
            timestamp=order.created_at,
            filled_quantity=order.filled_quantity,
            average_price=order.average_price
        )
    
    async def get_positions(self) -> List[Position]:
        """Get current simulated positions."""
        return list(self._positions.values())
    
    async def get_balance(self) -> Dict[str, float]:
        """Get simulated account balance."""
        return self._balance.copy()
    
    def set_historical_data(self, symbol: str, candles: List[Candle]) -> None:
        """Set historical data for simulation."""
        self._historical_data[symbol] = candles
        if candles:
            # Set current price to last candle close
            self._current_prices[symbol] = candles[-1].close
    
    def set_current_price(self, symbol: str, price: float) -> None:
        """Set current price for a symbol."""
        self._current_prices[symbol] = price
    
    async def _process_order(self, sim_order: SimulationOrder) -> None:
        """Process a simulated order."""
        request = sim_order.request
        symbol = request.symbol
        
        if symbol not in self._current_prices:
            sim_order.status = "cancelled"
            return
        
        current_price = self._current_prices[symbol]
        
        # Simple order matching simulation
        if request.order_type == "market":
            # Market orders are filled immediately at current price
            sim_order.status = "filled"
            sim_order.filled_quantity = request.quantity
            sim_order.average_price = current_price
            sim_order.filled_at = datetime.now()
            
            # Update positions and balance
            await self._update_positions_and_balance(request, current_price)
            
        elif request.order_type == "limit":
            # Limit orders are filled if price condition is met
            if (request.side == "buy" and current_price <= request.price) or \
               (request.side == "sell" and current_price >= request.price):
                sim_order.status = "filled"
                sim_order.filled_quantity = request.quantity
                sim_order.average_price = request.price
                sim_order.filled_at = datetime.now()
                
                # Update positions and balance
                await self._update_positions_and_balance(request, request.price)
    
    async def _update_positions_and_balance(self, request: OrderRequest, price: float) -> None:
        """Update positions and balance after order execution."""
        symbol = request.symbol
        quantity = request.quantity
        side = request.side
        
        # Calculate cost
        cost = quantity * price
        
        if side == "buy":
            # Update balance
            if "USDT" in self._balance:
                self._balance["USDT"] -= cost
            
            # Update positions
            if symbol in self._positions:
                position = self._positions[symbol]
                # Average down/up
                total_quantity = position.quantity + quantity
                total_cost = (position.entry_price * position.quantity) + cost
                position.entry_price = total_cost / total_quantity
                position.quantity = total_quantity
            else:
                # Create new position
                self._positions[symbol] = Position(
                    symbol=symbol,
                    side="long",
                    quantity=quantity,
                    entry_price=price,
                    current_price=price,
                    unrealized_pnl=0.0,
                    realized_pnl=0.0,
                    timestamp=datetime.now()
                )
        
        elif side == "sell":
            # Update balance
            if "USDT" in self._balance:
                self._balance["USDT"] += cost
            
            # Update positions (assuming we're selling from long position)
            if symbol in self._positions:
                position = self._positions[symbol]
                if position.quantity >= quantity:
                    position.quantity -= quantity
                    # Calculate realized PnL
                    pnl = (price - position.entry_price) * quantity
                    position.realized_pnl += pnl
                    
                    # Remove position if fully closed
                    if position.quantity == 0:
                        del self._positions[symbol]
    
    def get_simulation_state(self) -> Dict:
        """Get current simulation state for debugging."""
        return {
            "connected": self.connected,
            "orders_count": len(self._orders),
            "positions_count": len(self._positions),
            "balance": self._balance.copy(),
            "current_prices": self._current_prices.copy(),
            "symbols_with_data": list(self._historical_data.keys())
        } 
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
from data_provider.exchange_collection.async_exchange import AsyncExchange

from models.data_models.candle import Candle
from models.exchange_type import ExchangeType
from models.time_models import Interval


class AsyncBinanceExchange(AsyncExchange):
    """Async Binance exchange implementation."""

    def __init__(self, exchange_type: ExchangeType):
        super().__init__(exchange_type)
        self.base_url = "https://api.binance.com"
        self.websocket_url = "wss://stream.binance.com:9443/ws"
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[Any] = None
        self.__websocket_task__: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize the Binance exchange connection."""
        try:
            # Create HTTP session
            self.session = aiohttp.ClientSession()
            
            # Test connection
            if await self.test_connection():
                await self._set_initialized(True)
                if self.logger:
                    self.logger.info("Binance exchange initialized successfully")
            else:
                raise ConnectionError("Failed to connect to Binance API")

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize Binance exchange: {e}")
            raise

    async def get_exchange_name(self) -> str:
        """Get the name of the exchange."""
        return "Binance"

    async def fetch_product_list(self) -> List[str]:
        """Fetch the list of available trading products from Binance."""
        try:
            if not self.session:
                raise RuntimeError("Session not initialized")

            url = f"{self.base_url}/api/v3/exchangeInfo"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    symbols = []
                    
                    for symbol_info in data.get("symbols", []):
                        symbol = symbol_info.get("symbol")
                        status = symbol_info.get("status")
                        
                        # Only include active trading pairs
                        if symbol and status == "TRADING":
                            symbols.append(symbol)
                    
                    if self.logger:
                        self.logger.info(f"Fetched {len(symbols)} trading symbols from Binance")
                    
                    return symbols
                else:
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=response.status,
                        message=f"HTTP {response.status}"
                    )

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to fetch product list: {e}")
            raise

    async def fetch_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: Interval
    ) -> List[Candle]:
        """Fetch historical kline data from Binance."""
        try:
            if not self.session:
                raise RuntimeError("Session not initialized")

            # Convert interval to Binance format
            interval_str = self._convert_interval_to_binance(interval)
            
            # Convert dates to milliseconds
            start_ts = int(start_date.timestamp() * 1000)
            end_ts = int(end_date.timestamp() * 1000)

            url = f"{self.base_url}/api/v3/klines"
            params = {
                "symbol": symbol,
                "interval": interval_str,
                "startTime": start_ts,
                "endTime": end_ts,
                "limit": 1000  # Maximum allowed by Binance
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    candles = []
                    
                    for kline in data:
                        candle = self._parse_kline_to_candle(symbol, kline)
                        if candle:
                            candles.append(candle)
                    
                    if self.logger:
                        self.logger.info(f"Fetched {len(candles)} historical candles for {symbol}")
                    
                    return candles
                else:
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=response.status,
                        message=f"HTTP {response.status}"
                    )

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to fetch historical data for {symbol}: {e}")
            raise

    async def subscribe_to_websocket(
        self,
        symbols: List[str],
        interval: Interval
    ) -> bool:
        """Subscribe to real-time kline data via WebSocket."""
        try:
            if not symbols:
                return False

            # Convert interval to Binance format
            interval_str = self._convert_interval_to_binance(interval)
            
            # Create WebSocket streams for each symbol
            streams = []
            for symbol in symbols:
                stream_name = f"{symbol.lower()}@kline_{interval_str}"
                streams.append(stream_name)

            # Create WebSocket URL
            ws_url = f"{self.websocket_url}/{'/'.join(streams)}"
            
            # Start WebSocket connection
            self.__websocket_task__ = asyncio.create_task(
                self._handle_websocket(ws_url, symbols)
            )

            # Store subscription info
            self.__websocket_subscriptions__[f"kline_{interval_str}"] = {
                "symbols": symbols,
                "interval": interval,
                "streams": streams
            }

            if self.logger:
                self.logger.info(f"Subscribed to WebSocket for {len(symbols)} symbols")
            
            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to subscribe to WebSocket: {e}")
            return False

    async def unsubscribe_from_websocket(self) -> bool:
        """Unsubscribe from WebSocket data."""
        try:
            # Cancel WebSocket task
            if self.__websocket_task__ and not self.__websocket_task__.done():
                self.__websocket_task__.cancel()
                try:
                    await self.__websocket_task__
                except asyncio.CancelledError:
                    pass

            # Clear subscriptions
            self.__websocket_subscriptions__.clear()

            if self.logger:
                self.logger.info("Unsubscribed from WebSocket")
            
            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to unsubscribe from WebSocket: {e}")
            return False

    async def _handle_websocket(self, ws_url: str, symbols: List[str]):
        """Handle WebSocket connection and messages."""
        try:
            async with aiohttp.ClientSession() as ws_session:
                async with ws_session.ws_connect(ws_url) as websocket:
                    self.websocket = websocket
                    
                    if self.logger:
                        self.logger.info("WebSocket connected successfully")
                    
                    async for msg in websocket:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                                await self._process_websocket_message(data)
                            except json.JSONDecodeError:
                                if self.logger:
                                    self.logger.warning("Invalid JSON message received")
                            except Exception as e:
                                if self.logger:
                                    self.logger.error(f"Error processing WebSocket message: {e}")
                        
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            if self.logger:
                                self.logger.error("WebSocket error occurred")
                            break
                        
                        elif msg.type == aiohttp.WSMsgType.CLOSE:
                            if self.logger:
                                self.logger.info("WebSocket connection closed")
                            break

        except Exception as e:
            if self.logger:
                self.logger.error(f"WebSocket error: {e}")
        finally:
            self.websocket = None

    async def _process_websocket_message(self, data: Dict[str, Any]):
        """Process incoming WebSocket message."""
        try:
            # Check if it's a kline message
            if "k" in data:
                kline_data = data["k"]
                symbol = data["s"]  # Symbol
                
                # Create candle from kline data
                candle = self._parse_kline_to_candle(symbol, kline_data)
                if candle:
                    # Notify callbacks
                    await self._notify_candle_callbacks(candle)

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error processing WebSocket message: {e}")

    def _parse_kline_to_candle(self, symbol: str, kline_data: Dict[str, Any]) -> Optional[Candle]:
        """Parse Binance kline data to Candle object."""
        try:
            # Extract kline data
            open_time = int(kline_data.get("t", 0)) / 1000  # Convert from milliseconds
            open_price = float(kline_data.get("o", 0))
            high_price = float(kline_data.get("h", 0))
            low_price = float(kline_data.get("l", 0))
            close_price = float(kline_data.get("c", 0))
            volume = float(kline_data.get("v", 0))
            close_time = int(kline_data.get("T", 0)) / 1000  # Convert from milliseconds

            # Create Candle object
            candle = Candle(
                symbol=symbol,
                timestamp=open_time,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume
            )

            return candle

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error parsing kline data: {e}")
            return None

    def _convert_interval_to_binance(self, interval: Interval) -> str:
        """Convert internal interval to Binance format."""
        interval_map = {
            Interval.ONE_MINUTE: "1m",
            Interval.FIVE_MINUTES: "5m",
            Interval.FIFTEEN_MINUTES: "15m",
            Interval.ONE_HOUR: "1h",
            Interval.FOUR_HOURS: "4h",
            Interval.ONE_DAY: "1d"
        }
        return interval_map.get(interval, "1m")

    async def close(self) -> None:
        """Close the Binance exchange connection."""
        try:
            # Close WebSocket
            await self.unsubscribe_from_websocket()
            
            # Close HTTP session
            if self.session:
                await self.session.close()
                self.session = None
            
            # Call parent close method
            await super().close()
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error closing Binance exchange: {e}")

    async def get_ticker_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current ticker price for a symbol."""
        try:
            if not self.session:
                return None

            url = f"{self.base_url}/api/v3/ticker/price"
            params = {"symbol": symbol}

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get ticker price for {symbol}: {e}")
            return None

    async def get_24hr_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get 24-hour ticker statistics for a symbol."""
        try:
            if not self.session:
                return None

            url = f"{self.base_url}/api/v3/ticker/24hr"
            params = {"symbol": symbol}

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get 24hr ticker for {symbol}: {e}")
            return None 
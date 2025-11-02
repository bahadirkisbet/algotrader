"""
Binance WebSocket Implementation.

This module implements WebSocket operations for Binance exchange,
following SOLID principles and async best practices.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

import aiohttp

from models.data_models.candle import Candle
from models.time_models import Interval
from modules.exchange.exchange_websocket import ExchangeWebSocket


class BinanceWebSocket(ExchangeWebSocket):
    """
    Binance WebSocket implementation.

    Handles real-time data streaming from Binance including:
    - Kline/candlestick data
    - Trade data
    - Ticker data
    """

    def __init__(self):
        """Initialize Binance WebSocket manager."""
        super().__init__("wss://stream.binance.com:9443/ws")

        # Binance-specific state
        self.ws_session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> bool:
        """
        Establish WebSocket connection to Binance.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            if self.is_connected:
                if self.logger:
                    self.logger.warning("Already connected to Binance WebSocket")
                return True

            self.ws_session = aiohttp.ClientSession()
            await self.set_connected(True)

            if self.logger:
                self.logger.info("Binance WebSocket connection established")

            return True

        except Exception as e:
            if self.logger:
                self.logger.error("Failed to connect to Binance WebSocket: %s", e)
            return False

    async def disconnect(self) -> bool:
        """
        Close WebSocket connection.

        Returns:
            True if disconnection successful, False otherwise
        """
        try:
            # Cancel WebSocket task if running
            if self.websocket_task and not self.websocket_task.done():
                self.websocket_task.cancel()
                try:
                    await self.websocket_task
                except asyncio.CancelledError:
                    pass

            # Close WebSocket session
            if self.ws_session:
                await self.ws_session.close()
                self.ws_session = None

            await self.set_connected(False)

            if self.logger:
                self.logger.info("Binance WebSocket disconnected")

            return True

        except Exception as e:
            if self.logger:
                self.logger.error("Failed to disconnect from Binance WebSocket: %s", e)
            return False

    async def subscribe(self, symbols: List[str], interval: Interval) -> bool:
        """
        Subscribe to real-time kline data for given symbols.

        Args:
            symbols: List of trading pair symbols (e.g., ["BTCUSDT", "ETHUSDT"])
            interval: Time interval for candles

        Returns:
            True if subscription successful, False otherwise
        """
        try:
            if not self.is_connected:
                if not await self.connect():
                    return False

            if not symbols:
                return False

            # Convert interval to Binance format
            interval_str = self._interval_to_binance(interval)

            # Create stream names
            streams = []
            for symbol in symbols:
                stream_name = f"{symbol.lower()}@kline_{interval_str}"
                streams.append(stream_name)

            # Create WebSocket URL with combined streams
            ws_url = f"{self.websocket_url}/{'/'.join(streams)}"

            # Start WebSocket listening task
            self.websocket_task = asyncio.create_task(
                self._listen_to_stream(ws_url, symbols, interval)
            )

            # Store subscription info
            subscription_key = f"kline_{interval_str}"
            self.subscriptions[subscription_key] = {
                "symbols": symbols,
                "interval": interval,
                "streams": streams,
            }

            if self.logger:
                self.logger.info("Subscribed to Binance WebSocket for %s symbols", len(symbols))

            return True

        except Exception as e:
            if self.logger:
                self.logger.error("Failed to subscribe to Binance WebSocket: %s", e)
            return False

    async def unsubscribe(self, symbols: List[str], interval: Interval) -> bool:
        """
        Unsubscribe from data streams.

        Args:
            symbols: List of trading pair symbols to unsubscribe from
            interval: Time interval for candles

        Returns:
            True if unsubscription successful, False otherwise
        """
        try:
            interval_str = self._interval_to_binance(interval)
            subscription_key = f"kline_{interval_str}"

            if subscription_key in self.subscriptions:
                del self.subscriptions[subscription_key]

            # Cancel WebSocket task
            if self.websocket_task and not self.websocket_task.done():
                self.websocket_task.cancel()
                try:
                    await self.websocket_task
                except asyncio.CancelledError:
                    pass

            if self.logger:
                self.logger.info("Unsubscribed from Binance WebSocket")

            return True

        except Exception as e:
            if self.logger:
                self.logger.error("Failed to unsubscribe from Binance WebSocket: %s", e)
            return False

    async def _listen_to_stream(
        self, ws_url: str, _symbols: List[str], _interval: Interval
    ) -> None:
        """
        Listen to WebSocket stream and process messages.

        Args:
            ws_url: WebSocket URL
            _symbols: List of subscribed symbols (unused - for future use)
            _interval: Candle interval (unused - for future use)
        """
        try:
            async with self.ws_session.ws_connect(ws_url) as websocket:
                self.websocket = websocket

                if self.logger:
                    self.logger.info("Binance WebSocket stream connected successfully")

                async for msg in websocket:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                            await self._handle_message(data)
                        except json.JSONDecodeError:
                            if self.logger:
                                self.logger.warning("Invalid JSON message received")
                        except Exception as e:
                            if self.logger:
                                self.logger.error("Error processing WebSocket message: %s", e)

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        if self.logger:
                            self.logger.error("WebSocket error occurred")
                        break

                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        if self.logger:
                            self.logger.info("WebSocket connection closed")
                        break

        except asyncio.CancelledError:
            if self.logger:
                self.logger.info("WebSocket stream listener cancelled")
        except Exception as e:
            if self.logger:
                self.logger.error("WebSocket stream error: %s", e)
        finally:
            self.websocket = None

    async def _handle_message(self, message: Any) -> None:
        """
        Handle incoming WebSocket message and convert to Candle.

        Args:
            message: Raw WebSocket message from Binance
        """
        try:
            # Check if it's a kline message
            if "k" in message:
                kline_data = message["k"]
                symbol = message["s"]

                # Parse kline data to Candle
                candle = self._parse_kline_to_candle(symbol, kline_data)
                if candle:
                    # Notify all registered callbacks
                    await self.notify_candle_callbacks(candle)

        except Exception as e:
            if self.logger:
                self.logger.error("Error handling WebSocket message: %s", e)

    def _parse_kline_to_candle(self, symbol: str, kline_data: Dict[str, Any]) -> Optional[Candle]:
        """
        Parse Binance kline data to Candle object.

        Args:
            symbol: Trading pair symbol
            kline_data: Kline data from WebSocket message

        Returns:
            Candle object or None if parsing fails
        """
        try:
            candle = Candle(
                symbol=symbol,
                timestamp=int(kline_data.get("t", 0)),
                open=float(kline_data.get("o", 0)),
                high=float(kline_data.get("h", 0)),
                low=float(kline_data.get("l", 0)),
                close=float(kline_data.get("c", 0)),
                volume=float(kline_data.get("v", 0)),
                trade_count=int(kline_data.get("n", 0)),
            )
            return candle

        except Exception as e:
            if self.logger:
                self.logger.error("Error parsing kline data: %s", e)
            return None

    def _prepare_subscribe_message(self, symbol: str, interval: Interval) -> Dict[str, Any]:
        """
        Prepare Binance-specific subscription message.

        Note: Binance uses URL-based subscription, so this returns an empty dict.

        Args:
            symbol: Trading pair symbol
            interval: Candle interval

        Returns:
            Empty dictionary (Binance doesn't use message-based subscription)
        """
        return {}

    def _prepare_unsubscribe_message(self, symbol: str, interval: Interval) -> Dict[str, Any]:
        """
        Prepare Binance-specific unsubscription message.

        Note: Binance uses URL-based subscription, so this returns an empty dict.

        Args:
            symbol: Trading pair symbol
            interval: Candle interval

        Returns:
            Empty dictionary (Binance doesn't use message-based unsubscription)
        """
        return {}

    @staticmethod
    def _interval_to_binance(interval: Interval) -> str:
        """
        Convert internal interval to Binance format.

        Args:
            interval: Internal interval enum

        Returns:
            Binance interval string
        """
        interval_map = {
            Interval.ONE_MINUTE: "1m",
            Interval.FIVE_MINUTES: "5m",
            Interval.FIFTEEN_MINUTES: "15m",
            Interval.ONE_HOUR: "1h",
            Interval.FOUR_HOURS: "4h",
            Interval.ONE_DAY: "1d",
        }
        return interval_map.get(interval, "1m")

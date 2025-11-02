import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional

import websockets

from utils.dependency_injection_container import get


class WebSocketManager:
    """WebSocket manager for handling real-time data connections."""

    def __init__(self):
        self.logger: logging.Logger = get(logging.Logger)
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 1.0
        self.message_handlers: Dict[str, Callable] = {}
        self.connection_callbacks: List[Callable] = []
        self.disconnection_callbacks: List[Callable] = []

    async def connect(self, uri: str) -> bool:
        """Connect to a WebSocket server."""
        try:
            self.logger.info(f"Connecting to WebSocket: {uri}")

            self.websocket = await websockets.connect(uri)
            self.is_connected = True
            self.reconnect_attempts = 0

            self.logger.info("WebSocket connected successfully")

            # Notify connection callbacks
            await self.notify_connection_callbacks()

            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to WebSocket: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from the WebSocket server."""
        if self.websocket and self.is_connected:
            try:
                await self.websocket.close()
                self.logger.info("WebSocket disconnected")
            except Exception as e:
                self.logger.error(f"Error disconnecting WebSocket: {e}")
            finally:
                self.is_connected = False
                await self.notify_disconnection_callbacks()

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send a message through the WebSocket."""
        if not self.is_connected or not self.websocket:
            self.logger.warning("Cannot send message: WebSocket not connected")
            return False

        try:
            message_str = json.dumps(message)
            await self.websocket.send(message_str)
            return True

        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False

    async def receive_messages(self) -> None:
        """Receive and process incoming messages."""
        if not self.websocket:
            return

        try:
            async for message in self.websocket:
                await self.process_message(message)

        except websockets.exceptions.ConnectionClosed:
            self.logger.info("WebSocket connection closed")
            self.is_connected = False
            await self.notify_disconnection_callbacks()

        except Exception as e:
            self.logger.error(f"Error receiving messages: {e}")
            self.is_connected = False
            await self.notify_disconnection_callbacks()

    async def process_message(self, message: str) -> None:
        """Process a received message."""
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")

            if message_type in self.message_handlers:
                handler = self.message_handlers[message_type]
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            else:
                self.logger.debug(f"No handler for message type: {message_type}")

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse message as JSON: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    def register_message_handler(self, message_type: str, handler: Callable) -> None:
        """Register a handler for a specific message type."""
        self.message_handlers[message_type] = handler
        self.logger.debug(f"Registered handler for message type: {message_type}")

    def unregister_message_handler(self, message_type: str) -> None:
        """Unregister a message handler."""
        if message_type in self.message_handlers:
            del self.message_handlers[message_type]
            self.logger.debug(f"Unregistered handler for message type: {message_type}")

    def register_connection_callback(self, callback: Callable) -> None:
        """Register a callback for connection events."""
        if callback not in self.connection_callbacks:
            self.connection_callbacks.append(callback)

    def unregister_connection_callback(self, callback: Callable) -> None:
        """Unregister a connection callback."""
        if callback in self.connection_callbacks:
            self.connection_callbacks.remove(callback)

    def register_disconnection_callback(self, callback: Callable) -> None:
        """Register a callback for disconnection events."""
        if callback not in self.disconnection_callbacks:
            self.disconnection_callbacks.append(callback)

    def unregister_disconnection_callback(self, callback: Callable) -> None:
        """Unregister a disconnection callback."""
        if callback in self.disconnection_callbacks:
            self.disconnection_callbacks.remove(callback)

    async def notify_connection_callbacks(self) -> None:
        """Notify all connection callbacks."""
        for callback in self.connection_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                self.logger.error(f"Error in connection callback: {e}")

    async def notify_disconnection_callbacks(self) -> None:
        """Notify all disconnection callbacks."""
        for callback in self.disconnection_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                self.logger.error(f"Error in disconnection callback: {e}")

    async def start_listening(self) -> None:
        """Start listening for incoming messages."""
        if self.is_connected:
            await self.receive_messages()

    def get_connection_status(self) -> Dict[str, Any]:
        """Get the current connection status."""
        return {
            "connected": self.is_connected,
            "reconnect_attempts": self.reconnect_attempts,
            "message_handlers_count": len(self.message_handlers),
            "connection_callbacks_count": len(self.connection_callbacks),
            "disconnection_callbacks_count": len(self.disconnection_callbacks),
        }

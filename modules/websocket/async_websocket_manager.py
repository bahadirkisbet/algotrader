import asyncio
import configparser
import json
import logging
from abc import ABC
from typing import Callable, Dict, Optional

import websockets

from utils.di_container import get


class AsyncWebsocketManager(ABC):
    """Async websocket manager for handling multiple websocket connections."""
    
    WebsocketDict: Dict[str, websockets.WebSocketServerProtocol] = {}
    WebsocketConnectionCount: Dict[str, int] = {}
    MaxConnectionLimit: int = 50
    __tasks__: Dict[str, asyncio.Task] = {}
    __logger__: Optional[logging.Logger] = None

    @staticmethod
    async def initialize():
        """Initialize the websocket manager."""
        AsyncWebsocketManager.__logger__ = get(logging.Logger)

    @staticmethod
    def read_config(config: configparser.ConfigParser):
        """Read configuration for websocket manager."""
        AsyncWebsocketManager.MaxConnectionLimit = config["EXCHANGE"]["max_connection_limit"]

    @staticmethod
    async def create_websocket_connection(
        address: str, 
        port: int = None, 
        on_message: Callable = None,
        on_error: Callable = None, 
        on_close: Callable = None, 
        on_open: Callable = None
    ):
        """Create a new websocket connection."""
        socket_name = f"SOCKET_{len(AsyncWebsocketManager.WebsocketDict) + 1}"
        
        if (socket_name in AsyncWebsocketManager.WebsocketConnectionCount and 
                AsyncWebsocketManager.WebsocketConnectionCount[socket_name] < AsyncWebsocketManager.MaxConnectionLimit):
            # There is an available socket, use it
            AsyncWebsocketManager.WebsocketConnectionCount[socket_name] += 1
            return socket_name

        async def websocket_handler(websocket, path):
            """Handle websocket connection."""
            try:
                if on_open:
                    await on_open()
                
                async for message in websocket:
                    try:
                        msg = json.loads(message)
                        if on_message:
                            await on_message(msg)
                    except json.JSONDecodeError as e:
                        if on_error:
                            await on_error(e)
                    except Exception as e:
                        if on_error:
                            await on_error(e)
                            
            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                if on_close:
                    await on_close()
                AsyncWebsocketManager.end_connection(socket_name)

        url = address
        if port is not None:
            url += ":" + str(port)

        # Create websocket server
        server = await websockets.serve(
            websocket_handler,
            host=address,
            port=port,
            ssl=None  # Add SSL context if needed
        )
        
        AsyncWebsocketManager.WebsocketDict[socket_name] = server
        AsyncWebsocketManager.WebsocketConnectionCount[socket_name] = 1
        
        return socket_name

    @staticmethod
    async def start_connection(name: str):
        """Start a websocket connection."""
        if name in AsyncWebsocketManager.WebsocketDict:
            server = AsyncWebsocketManager.WebsocketDict[name]
            # The server is already running when created
            AsyncWebsocketManager.__logger__.info(f"Websocket connection {name} started")

    @staticmethod
    def end_connection(name: str):
        """End a websocket connection."""
        if name in AsyncWebsocketManager.WebsocketConnectionCount:
            if AsyncWebsocketManager.WebsocketConnectionCount[name] > 1:
                AsyncWebsocketManager.WebsocketConnectionCount[name] -= 1
            else:
                AsyncWebsocketManager.__remove_socket__(name)

    @staticmethod
    async def close():
        """Close all websocket connections."""
        for name in list(AsyncWebsocketManager.WebsocketDict.keys()):
            AsyncWebsocketManager.__remove_socket__(name)
        
        # Cancel all running tasks
        for task in AsyncWebsocketManager.__tasks__.values():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        AsyncWebsocketManager.__logger__.info("AsyncWebsocketManager closed")

    @staticmethod
    def __remove_socket__(name: str):
        """Remove a websocket socket."""
        if name in AsyncWebsocketManager.WebsocketDict:
            server = AsyncWebsocketManager.WebsocketDict[name]
            server.close()
            del AsyncWebsocketManager.WebsocketDict[name]
            del AsyncWebsocketManager.WebsocketConnectionCount[name]
            
        if name in AsyncWebsocketManager.__tasks__:
            task = AsyncWebsocketManager.__tasks__[name]
            if not task.done():
                task.cancel()
            del AsyncWebsocketManager.__tasks__[name] 
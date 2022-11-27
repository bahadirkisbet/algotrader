import configparser
import logging
from typing import Dict, Callable
from abc import abstractmethod, ABC
import json
import websocket


class WebsocketBase(ABC):
    WebsocketDict: Dict[str, websocket.WebSocketApp] = {}
    WebsocketConnectionCount: Dict[str, int] = {}
    MaxConnectionLimit: int = 50

    def __init__(self, url: str, config: configparser.ConfigParser, logger: logging.Logger):
        self.socket_name = f"SOCKET_{len(WebsocketBase.WebsocketDict)}"
        self.logger = logger
        self.config = config

    def __on_message__(self, ws: websocket.WebSocketApp, message):
        msg = json.loads(message)
        self.logger.info("Message has received: %s" % msg)
        on_message_callback(msg)

    def __on_error__(self, ws: websocket.WebSocketApp, error):
        self.logger.error(ws, error)
        on_error_callback(ws, error)

        WebsocketBase.WebsocketDict[self.socket_name] = websocket.WebSocketApp(
            url=url,
            on_message=self.__on_message__,
            on_error=self.__on_error__)
        WebsocketBase.WebsocketConnectionCount[self.socket_name] = 1

    @staticmethod
    def create(url: str, on_message: Callable, on_error: Callable):
        socket_name = f"SOCKET_{len(WebsocketBase.WebsocketDict)}"
        has_reached_max = socket_name in WebsocketBase.WebsocketConnectionCount and \
                          WebsocketBase.WebsocketConnectionCount[socket_name] < WebsocketBase.MaxConnectionLimit
        if has_reached_max:
            # there is an available socket, use it
            WebsocketBase.WebsocketConnectionCount[socket_name] += 1
            return socket_name
        return WebsocketBase(url, on_message)

    @abstractmethod
    def connect(self, url: str, message_callback: Callable, error_callback: Callable) -> None:
        pass

    @abstractmethod
    def send(self, socket_name, message):
        pass

    @abstractmethod
    def disconnect(self, socket_name):
        pass

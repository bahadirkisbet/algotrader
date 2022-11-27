import configparser
from typing import Dict, Callable, List
from abc import abstractmethod, ABC
import json
import websocket
import ssl
import threading


class WebsocketManager(ABC):
    WebsocketDict: Dict[str, websocket.WebSocketApp] = {}
    WebsocketConnectionCount: Dict[str, int] = {}
    MaxConnectionLimit: int = 50
    __tasks__: Dict[str, threading.Thread] = {}

    @staticmethod
    def read_config(config: configparser.ConfigParser):
        WebsocketManager.MaxConnectionLimit = config["EXCHANGE"]["max_connection_limit"]

    @staticmethod
    def create_websocket_connection(address: str, port: int = None, on_message: Callable = None,
                                    on_error: Callable = None, on_close: Callable = None, on_open: Callable = None):
        socket_name = f"SOCKET_{len(WebsocketManager.WebsocketDict) + 1}"
        if socket_name in WebsocketManager.WebsocketConnectionCount and \
                WebsocketManager.WebsocketConnectionCount[socket_name] < WebsocketManager.MaxConnectionLimit:
            # there is an available socket, use it
            WebsocketManager.WebsocketConnectionCount[socket_name] += 1
            return socket_name

        def on_message_wrapper(ws: websocket.WebSocketApp, message):
            msg = json.loads(message)
            if on_message is not None:
                on_message(msg)

        def on_error_wrapper(ws: websocket.WebSocketApp, error):
            if on_error is not None:
                on_error(error)

        def on_close_wrapper(ws: websocket.WebSocketApp, close_status_code, close_msg):
            if on_close is not None:
                on_close(close_status_code, close_msg)

        def on_open_wrapper(ws: websocket.WebSocketApp):
            if on_open is not None:
                on_open()

        url = address
        if port is not None:
            url += ":" + str(port)

        socket = websocket.WebSocketApp(
            url=url,
            on_message=on_message_wrapper,
            on_error=on_error_wrapper,
            on_close=on_close_wrapper,
            on_open=on_open_wrapper
        )
        WebsocketManager.WebsocketDict[socket_name] = socket
        WebsocketManager.WebsocketConnectionCount[socket_name] = 1
        return socket_name

    @staticmethod
    def start_connection(name):
        t = threading.Thread(
            target=WebsocketManager.WebsocketDict[name].run_forever,
            kwargs=dict(sslopt={"cert_reqs": ssl.CERT_NONE})
        )
        WebsocketManager.__tasks__[name] = t
        t.start()

    @staticmethod
    def end_connection(name):
        WebsocketManager.WebsocketDict[name].close()
        del WebsocketManager.__tasks__[name]
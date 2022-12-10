import time
from abc import ABC

import utils.websocket_manager.websocket_manager as websocket_manager


class Test1(ABC):
    test: str = "test1"
    test2: str = "test2"

    def print(self):
        print(self.test)


class Test2(Test1):
    test: str = "test2"

    def print(self):
        print(self.test)
        print(self.test2)


name = websocket_manager.WebsocketManager.create_websocket_connection(
    "wss://stream.binance.com:9443/ws/btcusdt@kline_1m",
    on_message=print,
    on_error=print,
    on_close=print,
    on_open=print,
)
websocket_manager.WebsocketManager.start_connection(name)
print('vbaha')
time.sleep(10)
print('kisbet')
websocket_manager.WebsocketManager.end_connection(name)
input()

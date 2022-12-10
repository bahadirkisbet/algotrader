import unittest
import utils.websocket_manager.websocket_manager as websocket_manager


class TestWebsocket(unittest.TestCase):
    test_url = "wss://stream.binance.com:9443/ws/btcusdt@kline_1m"

    def test_websocket_naming(self):
        name = websocket_manager.WebsocketManager.create_websocket_connection(
            self.test_url,
            on_message=print,
            on_error=print,
            on_close=print,
            on_open=print,
        )
        self.assertEqual(name, "SOCKET_1", "Websocket name is not correct")

    def test_websocket_connection(self):
        name = websocket_manager.WebsocketManager.create_websocket_connection(
            self.test_url,
            on_message=print,
            on_error=print,
            on_close=print,
            on_open=print,
        )
        self.assertEqual(name, "SOCKET_1", "Websocket name is not correct")


if __name__ == "__main__":
    unittest.main()

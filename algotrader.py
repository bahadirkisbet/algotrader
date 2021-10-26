from exchange import Exchange
from configs import CONFIG


class AlgoTrader:
    exchange: Exchange
    symbol: str
    cfg_field: str

    def __init__(self, _symbol, _cfg_field):
        self.exchange = Exchange(_symbol, CONFIG[_cfg_field], self.PIPE_exchange)
        self.symbol = _symbol
        self.cfg_field = _cfg_field

    # PIPES
    def PIPE_exchange(self, data: dict):

        if data["type"] == "history":
            self.symbol = data["msg"]
        elif data["type"] == "realtime":
            print(data["msg"])


if __name__ == "__main__":
    at = AlgoTrader("BTCUSDT", "BNB_spot")
    at.exchange.connect_to_websocket("5m")

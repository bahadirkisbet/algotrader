from exchange import ExchangeHandler


class AlgoTrader:
    exchange: ExchangeHandler
    symbol: str

    def __init__(self, sub):
        pass

    # PIPES
    def PIPE_exchange(self, data: dict):

        if data["type"] == "history":
            self.symbol = data["msg"]

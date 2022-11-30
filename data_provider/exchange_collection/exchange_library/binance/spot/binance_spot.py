from ..binance_base import *


class BinanceSpot(BinanceBase):
    """
        Binance is a cryptocurrency exchange.
        - https://www.binance.com/
    """

    def _on_message_(self, message):
        pass

    def _on_error_(self, error):
        pass

    def _on_close_(self, close_status_code, close_msg):
        pass

    def _on_open_(self):
        pass

    name: str = "BNB"
    exchange_type: ExchangeType = ExchangeType.SPOT
    websocket_url: str = "wss://stream.binance.com:9443/ws"
    api_url = "https://api.binance.com"
    api_endpoints: dict = {
        "fetch_candle": "/api/v3/klines?symbol={symbol}&interval={interval}&startTime={start}&endTime={end}",
        "fetch_product_list": "/api/v3/exchangeInfo"
    }

    def fetch_product_list(self):
        url = self.api_url + self.api_endpoints["fetch_product_list"]
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception("Error while fetching product list")

    def fetch_candle(self, symbol: str, startDate: datetime, endDate: datetime, interval: str) -> list:
        pass

    def subscribe_to_websocket(self, symbols: List[str], interval: Interval) -> None:
        pass

    def unsubscribe_from_websocket(self, symbol: str, interval: Interval) -> None:
        pass

    def __init__(self, config: configparser.ConfigParser, logger: logging.Logger):
        super().__init__(config, logger)

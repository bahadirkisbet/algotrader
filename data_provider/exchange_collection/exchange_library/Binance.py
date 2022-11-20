from ..exchange_base import *
import requests


class Binance(ExchangeBase):
    """
        Binance is a cryptocurrency exchange.
        - https://www.binance.com/
    """

    name: str = "BNB"
    websocket_url: str = "wss://stream.binance.com:9443/ws"
    api_url: str = "https://api.binance.com"
    api_endpoints: dict = {
        "fetch_candle": "/api/v3/klines?symbol={symbol}&interval={interval}&startTime={start}&endTime={end}",
        "fetch_product_list": "/api/v3/exchangeInfo"
    }

    def __init__(self, config: configparser.ConfigParser, logger: logging.Logger):
        super().__init__(config, logger)

    def fetch_candle(self, symbol: str, startDate: datetime, endDate: datetime, interval: str) -> list:
        pass

    def subscribe_to_websocket(self, symbols: List[str], interval: Interval) -> None:
        pass

    def unsubscribe_from_websocket(self, symbol: str, interval: Interval) -> None:
        pass

    def fetch_product_list(self):
        url = Binance.api_url + Binance.api_endpoints["fetch_product_list"]
        response = requests.get(url)
        return response.json()

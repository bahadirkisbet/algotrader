from ..binance_base import *


class BinanceFuture(BinanceBase):
    """
        Binance is a cryptocurrency exchange.
        - https://www.binance.com/
    """

    def _on_error_(self, error):
        pass

    def _on_close_(self, close_status_code, close_msg):
        pass

    def _on_open_(self):
        pass

    def _on_message_(self, message):
        pass

    def fetch_product_list(self):
        pass

    def fetch_candle(self, symbol: str, startDate: datetime, endDate: datetime, interval: str) -> list:
        pass

    def subscribe_to_websocket(self, symbols: List[str], interval: Interval) -> None:
        pass

    def unsubscribe_from_websocket(self, symbol: str, interval: Interval) -> None:
        pass


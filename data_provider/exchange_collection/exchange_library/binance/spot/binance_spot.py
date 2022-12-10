import multiprocessing
import multiprocessing.pool

from common_models.data_models.candle import Candle
from common_models.exchange_type import ExchangeType
from ..binance_base import *
import requests
import datetime


class BinanceSpot(BinanceBase):
    """
        Binance is a cryptocurrency exchange.
        - https://www.binance.com/
    """
    exchange_type: ExchangeType = ExchangeType.SPOT
    websocket_url: str = "wss://stream.binance.com:9443/ws"
    api_url = "https://api.binance.com"
    api_endpoints: dict = {
        "fetch_candle": "/api/v3/klines?symbol={symbol}&interval={interval}&startTime={start}&endTime={end}&limit=1000",
        "fetch_product_list": "/api/v3/exchangeInfo"
    }

    def __init__(self, config: configparser.ConfigParser, logger: logging.Logger):
        super().__init__(config, logger)

    def fetch_product_list(self) -> List[str]:
        assert "fetch_product_list" in self.api_endpoints, "fetch_product_list endpoint not defined"

        url = self.api_url + self.api_endpoints["fetch_product_list"]
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception("Error while fetching product list")
        json_data = response.json()
        # first filter by status == TRADING
        # then select only the symbol
        return [product["symbol"] for product in json_data["symbols"] if product["status"] == "TRADING"]

    def fetch_candle(self, symbol: str, startDate: datetime, endDate: datetime, interval: Interval) -> List[Candle]:
        assert "fetch_candle" in self.api_endpoints, "fetch_candle endpoint not defined"
        assert self.api_url is not None, "api_url not defined"

        url_list = self.__create_url_list__(endDate, interval, startDate, symbol)

        with multiprocessing.pool.ThreadPool() as pool:
            response_list = pool.starmap(self.__make_request__, url_list)
            result = [item for response in response_list if response is not None for item in response]

        return result

    def __make_request__(self, url):
        response = requests.get(url)
        if response.status_code != 200:
            self.logger.warning(f"Error while fetching candle - {response.status_code} - {response.text} - {url}")
            return None
        json = response.json()

        return [Candle(
            timestamp=int(item[0]),
            open=float(item[1]),
            high=float(item[2]),
            low=float(item[3]),
            close=float(item[4]),
            volume=float(item[5]),
            trade_count=int(item[8])
        ) for item in json]

    def __create_url_list__(self, endDate, interval, startDate, symbol):
        url_list = []
        current_date = startDate
        while current_date <= endDate:
            # noinspection PyTypeChecker
            next_date = current_date + datetime.timedelta(minutes=interval.value)
            url = self.api_url + self.api_endpoints["fetch_candle"].format(
                symbol=symbol,
                interval=self.interval_to_granularity(interval),
                start=int(current_date.timestamp() * 1000),
                end=int(next_date.timestamp() * 1000)
            )
            url_list.append([url])
            current_date = next_date
        return url_list

    # SOCKET RELATED METHODS #

    def subscribe_to_websocket(self, symbols: List[str], interval: Interval) -> None:
        pass

    def unsubscribe_from_websocket(self, symbol: str, interval: Interval) -> None:
        pass

    def _on_message_(self, message):
        pass

    def _on_error_(self, error):
        pass

    def _on_close_(self, close_status_code, close_msg):
        pass

    def _on_open_(self):
        pass

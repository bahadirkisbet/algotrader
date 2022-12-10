from data_provider.exchange_collection.exchange_base import *
from common_models.time_models import Interval
import datetime


class BinanceBase(ExchangeBase, ABC):
    """
        Binance is a cryptocurrency exchange.
        - https://www.binance.com/
    """
    name: str = "BNB"
    websocket_url: str | None = None
    api_url: str | None = None
    api_endpoints: dict | None = None

    def __init__(self, config: configparser.ConfigParser, logger: logging.Logger):
        super().__init__(config, logger)

    def interval_to_granularity(self, interval: Interval) -> object:
        match interval:
            case Interval.ONE_MINUTES:
                return "1m"
            case Interval.FIVE_MINUTES:
                return "5m"
            case Interval.FIFTEEN_MINUTES:
                return "15m"
            case Interval.ONE_HOUR:
                return "1h"
            case Interval.ONE_DAY:
                return "1d"
            case _:
                raise Exception("Interval not supported")

    def _create_url_list_(self, endDate, interval, startDate, symbol):
        url_list = []
        current_date = startDate
        while current_date <= endDate:
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

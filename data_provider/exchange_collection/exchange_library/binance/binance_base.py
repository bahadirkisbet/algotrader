from data_provider.exchange_collection.exchange_base import *
from common_models.time_models import Interval


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

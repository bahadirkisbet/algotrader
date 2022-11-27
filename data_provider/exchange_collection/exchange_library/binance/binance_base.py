from data_provider.exchange_collection.exchange_base import *
import requests
from common_models.time_models import Interval
from common_models.exchange_type import ExchangeType


class BinanceBase(ExchangeBase):
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

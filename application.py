from common_models.exchange_type import ExchangeType
from data_provider.exchange_collection.exchange_factory import ExchangeFactory
from data_provider.exchange_collection.exchange_library.binance.binance_base import *
from setup import *

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read("config.ini")
    logger = logger_setup(config)
    exchange_code = "BNB"
    exchange_type = ExchangeType.SPOT

    service: ExchangeBase = ExchangeFactory.create(exchange_code, exchange_type, config, logger)
    input()

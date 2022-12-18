from common_models.exchange_type import ExchangeType
from data_provider.exchange_collection.exchange_factory import ExchangeFactory
from data_provider.exchange_collection.exchange_library.binance.binance_base import *
from utils.config_manager.config_manager import ConfigManager
from utils.log_manager.log_manager import LogManager

if __name__ == "__main__":
    config = ConfigManager.get_config()
    logger = LogManager.get_logger(config)
    exchange_code = "BNB"
    exchange_type = ExchangeType.SPOT

    service: ExchangeBase = ExchangeFactory.create(exchange_code, exchange_type, config, logger)
    input()

from data_provider.exchange_collection.exchange_base import *
from common_models.exchange_type import ExchangeType
import configparser

from data_provider.exchange_collection.exchange_library.binance.spot.binance_spot import BinanceSpot
from data_provider.exchange_collection.exchange_library.binance.futures.binance_futures import BinanceFutures


class ExchangeFactory:
    @staticmethod
    def create(exchange_name, exchange_type: ExchangeType, config: configparser.ConfigParser, logger: logging.Logger) -> ExchangeBase:
        match exchange_type:
            case ExchangeType.SPOT:
                return ExchangeFactory.__create_spot__(exchange_name, config, logger)
            case ExchangeType.FUTURES:
                return ExchangeFactory.__create_futures__(exchange_name, config, logger)
            case _:
                raise Exception("Unknown exchange type")

    @staticmethod
    def __create_spot__(exchange_name, config: configparser.ConfigParser, logger: logging.Logger) -> ExchangeBase:
        match exchange_name:
            case "BNB":
                return BinanceSpot(config, logger)
            case _:
                raise Exception("Unknown exchange")

    @staticmethod
    def __create_futures__(exchange_name, config: configparser.ConfigParser, logger: logging.Logger) -> ExchangeBase:
        match exchange_name:
            case "BNB":
                return BinanceFutures(config, logger)
            case _:
                raise Exception("Unknown exchange")
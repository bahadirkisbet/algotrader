from common_models.exchange_type import ExchangeType
from data_provider.exchange_collection.exchange_base import *
from data_provider.exchange_collection.exchange_library.binance_spot import BinanceSpot


class ExchangeFactory:
    @staticmethod
    def create(
            exchange_name: str,
            exchange_type: ExchangeType) -> ExchangeBase:

        match exchange_type:
            case ExchangeType.SPOT:
                return ExchangeFactory.__create_spot__(exchange_name)
            case _:
                raise Exception("Unknown exchange type")

    @staticmethod
    def __create_spot__(exchange_name) -> ExchangeBase:
        match exchange_name:
            case "BNB":
                return BinanceSpot()
            case _:
                raise Exception("Unknown exchange")


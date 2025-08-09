from data_provider.exchange_collection.exchange_base import *
from data_provider.exchange_collection.exchange_library.binance_spot import Binance

from models.exchange_type import ExchangeType


class ExchangeFactory:
    @staticmethod
    def create(
            exchange_name: str,
            exchange_type: ExchangeType) -> Exchange:

        match exchange_type:
            case ExchangeType.SPOT:
                return ExchangeFactory.__create_spot__(exchange_name)
            case _:
                raise Exception("Unknown exchange type")

    @staticmethod
    def __create_spot__(exchange_name) -> Exchange:
        match exchange_name:
            case "BNB":
                return Binance()
            case _:
                raise Exception("Unknown exchange")


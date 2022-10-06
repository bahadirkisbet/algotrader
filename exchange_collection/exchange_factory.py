from exchange_collection.exchange_library.FTX import *
import configparser


class ExchangeFactory:
    @staticmethod
    def create(exchange_name, config: configparser.ConfigParser, logger: logging.Logger) -> ExchangeBase:
        match exchange_name:
            case "FTX":
                return FTX(config, logger)
            case _:
                raise Exception("Unknown exchange")
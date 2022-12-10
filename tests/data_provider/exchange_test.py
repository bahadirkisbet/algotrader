import datetime
import unittest

from data_provider.exchange_collection.exchange_factory import *
from setup import *


class TestExchangeBase(unittest.TestCase):
    exchange_code: str = "BNB"
    exchange_type: ExchangeType = ExchangeType.SPOT

    @staticmethod
    def prepare_config_and_logger():
        config = configparser.ConfigParser()
        config.read("../../config.ini")
        logger = logger_setup(config)
        return config, logger

    def test_product_list(self):
        config, logger = self.prepare_config_and_logger()
        exchange: ExchangeBase = ExchangeFactory.create(
            TestExchangeBase.exchange_code,
            TestExchangeBase.exchange_type,
            config,
            logger)

        product_list = exchange.fetch_product_list()
        self.assertIsNotNone(product_list, "Product list is empty")
        self.assertEqual(type(product_list), dict, "Product list is not a dict")

    def test_candle(self):
        config, logger = self.prepare_config_and_logger()
        exchange: ExchangeBase = ExchangeFactory.create(
            TestExchangeBase.exchange_code,
            TestExchangeBase.exchange_type,
            config,
            logger)
        symbol = "BTCUSDT"
        start_date = datetime.datetime(2021, 1, 1)
        end_date = datetime.datetime(2021, 12, 2)
        candles = exchange.fetch_candle(symbol, start_date, end_date, Interval.ONE_DAY)
        self.assertIsNotNone(candles, "Candles are empty")


if __name__ == "__main__":
    unittest.main()

import datetime
import unittest

from data_provider.exchange_collection.exchange_factory import (
    Exchange,
    ExchangeFactory,
    ExchangeType,
    Interval,
)




class TestExchangeBase(unittest.TestCase):
    exchange_code: str = "BNB"
    exchange_type: ExchangeType = ExchangeType.SPOT

    @staticmethod
    def prepare_config_and_logger():
        from utils.service_initializer import initialize_services
        import asyncio
        asyncio.run(initialize_services())
        from utils.dependency_injection_container import get
        import configparser
        import logging
        config = get(configparser.ConfigParser)
        config.read("../../config.ini")
        logger = get(logging.Logger)
        return config, logger

    def test_product_list(self):
        exchange: Exchange = ExchangeFactory.create(
            TestExchangeBase.exchange_code,
            TestExchangeBase.exchange_type)

        product_list = exchange.fetch_product_list()
        self.assertIsNotNone(product_list, "Product list is empty")
        self.assertEqual(type(product_list), dict, "Product list is not a dict")

    def test_candle(self):
        exchange: Exchange = ExchangeFactory.create(
            TestExchangeBase.exchange_code,
            TestExchangeBase.exchange_type)
        symbol = "BTCUSDT"
        start_date = datetime.datetime(2021, 1, 1)
        end_date = datetime.datetime(2022, 1, 1)
        candles = exchange.fetch_candle(symbol, start_date, end_date, Interval.FIVE_MINUTES)
        self.assertIsNotNone(candles, "Candles are empty")


if __name__ == "__main__":
    unittest.main()

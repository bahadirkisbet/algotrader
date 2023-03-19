import datetime
import unittest

from data_provider.exchange_collection.exchange_factory import ExchangeType, ExchangeFactory, Exchange, Interval
from managers.service_manager import ServiceManager


class TestExchangeBase(unittest.TestCase):
    exchange_code: str = "BNB"
    exchange_type: ExchangeType = ExchangeType.SPOT

    @staticmethod
    def prepare_config_and_logger():
        ServiceManager.initialize_config()
        ServiceManager.initialize_logger()
        config = ServiceManager.get_service("config")
        config.read("../../config.ini")
        logger = ServiceManager.get_service("logger")
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

import unittest
from data_provider.exchange_collection.exchange_factory import *
from setup import *


class TestExchangeBase(unittest.TestCase):
    exchange_code: str = "BNB"
    exchange_type: ExchangeType = ExchangeType.SPOT

    def test_product_list(self):
        config = configparser.ConfigParser()
        config.read("../../config.ini")
        logger = logger_setup(config)
        exchange: ExchangeBase = ExchangeFactory.create(
            TestExchangeBase.exchange_code,
            TestExchangeBase.exchange_type,
            config,
            logger)

        product_list = exchange.fetch_product_list()
        self.assertIsNotNone(product_list, "Product list is empty")
        self.assertEqual(type(product_list), dict, "Product list is not a dict")
        print(product_list)


if __name__ == "__main__":
    unittest.main()

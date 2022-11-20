from data_provider.exchange_collection.exchange_library.Binance import *
from setup import *

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read("config.ini")
    logger = logger_setup(config)

    service: ExchangeBase = Binance(config, logger)
    service.register_callbacks([print])
    service.subscribe_to_websocket(["BTC-PERP"], Interval.ONE_MINUTES)
    input()



# service.fetch_candle("BTC/USDT", datetime(2017, 1, 1, 0, 0, 0), datetime.now(), Interval.ONE_HOUR)

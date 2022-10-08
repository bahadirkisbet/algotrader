import exchange_collection
from setup import *
from exchange_collection.exchange_library.FTX import *

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read("config.ini")
    logger = logger_setup(config)

    service: ExchangeBase = FTX(config, logger)
    service.register_callbacks([print])
    service.subscribe_to_websocket("BTC/USD", Interval.ONE_MINUTES)
    input()



# service.fetch_candle("BTC/USDT", datetime(2017, 1, 1, 0, 0, 0), datetime.now(), Interval.ONE_HOUR)

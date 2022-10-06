import exchange_collection
from setup import *
from exchange_collection.exchange_base import *
from exchange_collection.exchange_library.FTX import *

config = configparser.ConfigParser()
config.read("config.ini")
logger = logger_setup(config)

service: ExchangeBase = FTX(config, logger)


if __name__ == "__main__":
    pass



# service.fetch_candle("BTC/USDT", datetime(2017, 1, 1, 0, 0, 0), datetime.now(), Interval.ONE_HOUR)

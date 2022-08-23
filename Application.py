import ExchangeCollection
from Setup import *
from ExchangeCollection.ExchangeBase import *
from ExchangeCollection.ExchangeLibrary.FTX import *

config = configparser.ConfigParser()
config.read("config.ini")
logger = logger_setup(config)


service: ExchangeBase = FTX(config, logger)

#service.fetch_candle("BTC/USDT", datetime(2017, 1, 1, 0, 0, 0), datetime.now(), Interval.ONE_HOUR)

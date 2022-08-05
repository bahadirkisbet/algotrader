from ExchangeCollection.ExchangeBase import *
from ExchangeCollection.FTX import *

service: ExchangeBase = FTX()

service.fetch_candle("BTC/USDT", datetime(2017, 1, 1, 0, 0, 0), datetime.now(), Interval.ONE_HOUR)
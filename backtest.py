from exchange import *
from ta.momentum import rsi

COINS = {
    "BTCUSDT",
    "ETHUSDT",
    "XRPUSDT"
}

exchange_service = ExchangeService()
a = exchange_service.aggregate_candles("BTCUSDT", current_ms() - 300000*1000*10)
for i in a:
    print(a[i].shape)

tt = time.time()
print(rsi(a["5m"]["close"]))
print(time.time() - tt)
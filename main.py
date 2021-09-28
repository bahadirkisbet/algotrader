from exchange import *

COINS = {
    "BTCUSDT",
    "ETHUSDT",
    "XRPUSDT"
}

exchange_service = ExchangeService()
exchange_service.aggregate_candles("BTCUSDT", current_ms() - 300000*1000*9)
from models.data_models.candle import Candle

candle = Candle("BTCUSDT", 1610000000, 1, 2, 3, 4, 5, 6)
print(candle)
print(candle.get_json())


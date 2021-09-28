from Helper import *
import pandas as pd


class IndicatorHandler:
    indicator_instance_list: list
    candles: pd.DataFrame
    indicator_values: dict

    def __init__(self, _candles, _indicator_list):
        self.indicator_list = self.parse_indicator_list(_indicator_list)
        self.candles = _candles
        self.indicator_values = dict()

    def parse_indicator_list(self, _indicator_list):
        res = list()
        for i in _indicator_list:
            temp = i.split("_")
            res.append([temp[0]] + list(map(lambda x: eval(x), temp[1:])))
            self.indicator_values[i] = list()

        return res

    def add_candles(self, _candles: pd.DataFrame):

        try:
            for i in range(_candles.shape[0]):
                self.candles = self.candles.append({
                    "open_time": _candles.iloc[i]["open_time"],
                    "open": _candles.iloc[i]["open"],
                    "high": _candles.iloc[i]["high"],
                    "low": _candles.iloc[i]["low"],
                    "close": _candles.iloc[i]["close"],
                    "volume": _candles.iloc[i]["volume"],
                    "close_time": _candles.iloc[i]["close_time"],
                    "quote_asset_volume": _candles.iloc[i]["quote_asset_volume"],
                    "number_of_trades": _candles.iloc[i]["number_of_trades"],
                    "taker_buy_asset_volume": _candles.iloc[i]["taker_buy_asset_volume"],
                    "taker_buy_quote_volume": _candles.iloc[i]["taker_buy_quote_volume"],
                    "nothing": _candles.iloc[i]["nothing"]
                }, ignore_index=True)
                self.update_indicator_values()
        except:
            print("error")

    def update_indicator_values(self):
        for indicator in self.indicator_list:

            try: # All indicators will be added in this block to be called in every candle update
                if indicator[0] == "BB":
                    self.BollingerBands(*indicator[1:])

            except TypeError as err:
                print(str(err))

    # REGION : INDICATORS

    def BollingerBands(self, length, std):
        if length > len(self.indicator_values["BB"]):
            self.indicator_values["BB"].append(None)
        else:
            sma = self.indicator_values["SMA_20"][-1]
            std = self.indicator_values["STD_20"][-1]
            return [sma - std, sma, sma + std]


    # END REGION

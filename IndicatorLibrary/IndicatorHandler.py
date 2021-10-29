from algotrader import CONFIG
from math import sqrt

class IndicatorHandler:
    indicator_instance_list: set
    candles: list
    indicator_values: dict
    cfg: dict  # config file

    def __init__(self, _candles, _indicator_list, _indicator_values):
        self.candles = _candles
        self.indicator_values = _indicator_values
        self.indicator_instance_list = self.parse_indicator_list(_indicator_list)
        self.cfg = CONFIG

    def parse_indicator_list(self, _indicator_list):
        res = set()
        for i in _indicator_list:
            temp = i.split("_")
            temp = tuple([temp[0]] + list(map(int, temp[1:])))
            res.add(temp)
            self.indicator_values[temp] = list()

        return res

    def update_indicator_values(self, src=0, ind=-1):
        for indicator in self.indicator_instance_list:
            try:  # All indicators will be added in this block to be called in every candle update
                if indicator[0] == "BB":
                    self.BollingerBands(ind, src, *indicator[1:])

            except TypeError as err:
                print(str(err))

    # REGION : INDICATORS

    def BollingerBands(self, ind, src, length, std):
        field = ("BB", length, std)
        if length > ind + 1:
            self.indicator_values[field].append(None)
        else:
            sum = 0
            for i in self.candles[ind - length + 1 : ind + 1]:
                sum += i[src]
            sma = sum / length

            mean_diff = 0
            for i in self.candles[ind - length + 1 : ind + 1]:
                mean_diff += (i[src] - sma) * (i[src] - sma)
            std = sqrt(mean_diff / length)
            self.indicator_values[field].append([sma - std, sma, sma + std])
    #
    # def SimpleMovingAverage(self, length):
    #     if length > len(self.indicator_values[])

    # END REGION


if __name__ == "__main__":
    indicator_list = ["BB_20_2"]
    test_dict = {
        5: [[5],[6],[1],[8],[1],
            [4],[7],[3],[10],[12],
            [1],[5],[2],[3],[4],
            [6],[8],[10],[11],[14]]
    }
    values = dict()
    ih = IndicatorHandler(test_dict[5], indicator_list, values)
    print(ih.indicator_instance_list)

    for i in range(20):
        ih.update_indicator_values(0, i)
    print(ih.candles)



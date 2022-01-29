from abc import abstractmethod
from IExchangeBase import ExchangeInterface


class Exchange(ExchangeInterface):
    """
    Exchange class
    """
    @abstractmethod
    def get_candles(self, url: str, start_time: int, end_time: int, time_interval: int, body: str) -> None:
        pass

    def __init__(self, exchange_name):
        """
        Constructor
        :param exchange_name:
        """
        super().__init__()
        self.exchange_name = exchange_name

    def get_exchange_name(self):
        """
        Get exchange name
        :return:
        """
        return self.exchange_name


class Test(Exchange):
    """
    Test class
    """

    def get_candles(self, url: str, start_time: int, end_time: int, time_interval: int, body: str) -> None:
        pass

    def __init__(self):
        """
        Constructor
        """
        super().__init__("Test")


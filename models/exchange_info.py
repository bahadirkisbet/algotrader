import datetime

from models.exchange_type import ExchangeType


class ExchangeInfo:
    def __init__(
        self, name: str, first_data_datetime: datetime.datetime, exchange_type: ExchangeType
    ):
        self.name: str = name
        self.first_data_datetime: datetime.datetime = first_data_datetime
        self.exchange_type: ExchangeType = exchange_type

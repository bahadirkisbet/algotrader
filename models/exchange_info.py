import datetime


class ExchangeInfo:
    def __init__(self, name: str, first_data_datetime: datetime.datetime):
        self.name: str = name
        self.first_data_datetime: datetime.datetime = first_data_datetime

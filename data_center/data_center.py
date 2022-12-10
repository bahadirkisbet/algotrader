from abc import ABC


class DataCenter(ABC):
    def __init__(self):
        self.__buffer__ = []

    def on_message(self, data):
        pass

    def on_error(self, error):
        pass

    def on_close(self, close_status_code, close_msg):
        pass

    def on_open(self):
        pass
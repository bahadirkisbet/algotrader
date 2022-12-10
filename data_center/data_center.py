class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class DataCenter(metaclass=Singleton):
    def __init__(self, num):
        self.__buffer__ = []
        self.test = num

    def on_message(self, data):
        pass

    def on_error(self, error):
        pass

    def on_close(self, close_status_code, close_msg):
        pass

    def on_open(self):
        pass

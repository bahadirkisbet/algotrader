from abc import ABC, abstractmethod


class Strategy(ABC):

    @abstractmethod
    def train(self, data):
        pass

    @abstractmethod
    def predict(self, data):
        pass


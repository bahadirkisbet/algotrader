from abc import ABC

from data_center.data_center import DataCenter


class Test1(ABC):
    test: str = "test1"
    test2: str = "test2"

    def print(self):
        print(self.test)


class Test2(Test1):
    test: str = "test2"

    def print(self):
        print(self.test)
        print(self.test2)


test = DataCenter(1)
test2 = DataCenter(2)
print(test.test)
print(test2.test)

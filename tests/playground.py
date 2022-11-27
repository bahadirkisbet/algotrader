from abc import abstractmethod, ABC

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


t1 = Test1()
t2 = Test2()
t1.print()
t2.print()

import threading
import time


class a:
    def __init__(self, _arr):
        self.arr = _arr
        self.arr.append(3)


    def t(self):
        for i in range(10):
            self.f(i)
            time.sleep(1)

class b:
    arr: list
    def __init__(self):
        self.arr = list()
        print(self.arr)
        test = a(self.arr)
        print(self.arr)



    def update(self, num):
        print(num)


import threading
import time


class ThreadingExample(object):
    """ Threading example class
    The run() method will be started and it will run in the background
    until the application exits.
    """

    def __init__(self, interval=1):
        """ Constructor
        :type interval: int
        :param interval: Check interval, in seconds
        """
        self.interval = interval

        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True                            # Daemonize thread
        thread.start()                                  # Start the execution

    def run(self):
        """ Method that runs forever """
        while True:
            # Do something
            print('Doing something imporant in the background')

            time.sleep(self.interval)

b()
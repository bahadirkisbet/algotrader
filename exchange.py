import sys
import time

import requests
import json
import websocket
import threading
from tqdm import tqdm
from math import ceil
from utils import current_ms
from typing import Any
from configs import CONFIG
from queue import Queue


class Exchange:
    cfg: dict
    data: dict
    pipe: Any
    symbol: str
    sckt: websocket.WebSocket
    thread: threading.Thread
    __close_connection__: threading.Event

    def __init__(self, _symbol, _cfg, _pipe, _file_path=""):
        """
        :param _cfg: config file for an exchange
        :param _pipe: a pipeline for the communication between other classes
        :param _file_path: if there is an archive in the file, read it
        """
        self.symbol = _symbol
        self.cfg = _cfg
        self.pipe = _pipe
        self.sckt = websocket.WebSocket()
        self.data = dict()
        self.__close_connection__ = threading.Event()
        if _file_path != "":  # there is a path given
            pass
            # self.read_data(_file_path)

    def get_available_coins(self):
        url = self.cfg["endpoints"]["api"] + self.cfg["endpoints"]["coins"]
        req = requests.get(url)
        return req.content

    def get_candles(self, interval, start_time=None, end_time=None):

        if start_time is None:
            start_time = self.cfg["first_ts"]

        url = self.cfg["endpoints"]["api"] + self.cfg["endpoints"]["candles"]

        current_time = start_time
        last_time = end_time if end_time is not None else current_ms()

        conccurrent_queue = Queue()
        time_gap = 300000

        total_num = ceil((last_time - current_time) / time_gap)
        progress_bar = tqdm(total=total_num)  # visual and simple progress bar
        t = None
        while current_time < last_time:
            progress_bar.update(1)  # everytime, it increases progress by one

            st = current_time
            ft = current_time + time_gap
            # The request body prepared by the user. The next line can be changed by the parameters
            body = eval(self.cfg["request_body"]["candle"] % (self.symbol, self.cfg["intervals"][interval], st, ft))
            t = threading.Thread(target=self.make_request, args=(url, body, conccurrent_queue))
            t.start()

            time.sleep(self.cfg["throttle_ms"] / 1000)

            # req = requests.get(url, params=body).content
            current_time += time_gap
        t.join(2)
        result = list(filter(lambda x: x != [], conccurrent_queue.queue))
        result.sort(key=lambda x: x[0])
        return [ i[0] for i in result ]

    def make_request(self, url, body, queue: Queue):
        req = requests.get(url, params=body).content
        queue.put(list(map(lambda x: list(map(float, x)), eval(req))))


    def save_data(self, key, path):
        try:
            file_name = f"{self.cfg['exchange_code']}_{self.symbol}_{key}.json"
            with open(path + file_name, 'w') as out:
                json.dump(self.data[key], out)

        except Exception as e:
            print(e)

    def read_data(self, key, path):
        try:
            with open(path, 'r') as in_file:
                self.data[key] = json.load(in_file)

        except Exception as e:
            print(e)

    def retrieve_missing_candles(self, key, path):
        self.read_data(key, path)  # read the data
        last_ts = self.data[key][-1][self.cfg["map"]["c_ts"]]
        self.data[key].extend(self.get_candles(key, last_ts))

    def connect_to_websocket(self, interval):
        self.thread = threading.Thread(target=self.__socket_connection, args=(interval,))
        self.thread.start()

    def close_connection(self):
        self.close_connection.set()

    def __socket_connection(self, interval):

        symbol = self.symbol.lower()
        url = self.cfg["endpoints"]["websocket"]
        url += self.cfg["endpoints"]["websocket_extra"] % (symbol, interval)

        self.sckt.connect(url)
        if self.sckt.connected:
            print("Connection is successful")
        else:
            print("There is a problem in connection")

        sub_msg = self.cfg["request_body"]["subscribe"] % (symbol, 'kline', self.cfg["intervals"][interval])
        sub_msg = json.dumps(eval(sub_msg))  # Somehow, it gives an error if you convert it into dict and then string.

        self.sckt.send(sub_msg)
        while not self.__close_connection__.is_set():

            msg = json.loads(self.sckt.recv())
            print(msg)
            if "e" in msg:
                if msg["e"] == "kline" and "k" in msg and msg["k"]["x"]:
                    self.pipe({
                        "type": "realtime",
                        "msg": msg
                    })
        print("WebSocket is closed")
        sys.exit()


def f(x):
    print(x)


if __name__ == "__main__":
    exchange = Exchange("BTCUSDT", CONFIG["BNB_spot"], f)
    a_month_ago = 1 * 24 * 60 * 60 * 1000
    exchange.data[5] = exchange.get_candles(5, start_time=current_ms() - a_month_ago)
    exchange.save_data(5, ".")
    # exchange.connect_to_websocket(5)
    # exchange.retrieve_missing_candles(5, "archive/BNB_BTCUSDT_5.json")
    exchange.read_data(5, ".BNB_BTCUSDT_5.json")
    gap = 300000
    wrong_time = 0
    s = set()
    # exchange.data[5] = list(map(lambda x: x[0], exchange.data[5]))

    for i in range(len(exchange.data[5]) - 1):
        if exchange.data[5][i + 1][0] - exchange.data[5][i][0] != gap:
            wrong_time += 1
        s.add(exchange.data[5][i][0])
    s.add(exchange.data[5][-1][0])
    print(wrong_time)
    print(len(s), len(exchange.data[5]))

    # exchange.get_candles(5)
    # exchange.save_data(5, "archive/")
    # exchange.retrieve_missing_candles(5, "archive/BNB_BTCUSDT_5.json")
    # print(len(exchange.data[5]))

import configparser
import json
import logging
import os
import gzip
from typing import List

from common_models.data_models.candle import Candle


class ArchiveManager:
    def __init__(self, logger: logging.Logger, config: configparser.ConfigParser):
        self.logger: logging.Logger = logger
        self.config: configparser.ConfigParser = config
        self.__archive_folder__ = self.config["DEFAULT"]["archive_folder"]
        self.__default_encoding__ = "utf-8"

        self.__create_archive_folder_if_not_exists__()

    def __create_archive_folder_if_not_exists__(self):
        if not os.path.exists(self.__archive_folder__):
            os.mkdir(self.__archive_folder__)

    def save(self,
             exchange_code: str,
             symbol: str,
             data_type: str,
             data_frame: str,
             data: List[Candle]):

        file_name = f"{self.__archive_folder__}/{exchange_code}_{data_type}_{symbol}_{data_frame}.json.gz"
        json_dict = {
            "fields": Candle.get_fields(),
            "data": [candle.get_json().values() for candle in data]
        }
        json_str = json.dumps(json_dict).encode(self.__default_encoding__)
        with gzip.open(file_name, "w") as out:
            out.write(json_str)

    def read(self, exchange_code: str,
             symbol: str,
             data_type: str,
             data_frame: str):
        file_name = f"{self.__archive_folder__}/{exchange_code}_{data_type}_{symbol}_{data_frame}.json.gz"

        if not os.path.exists(file_name):
            return []

        with gzip.open(file_name, "r") as f_in:
            json_str = f_in.read().decode(self.__default_encoding__)
        return [Candle(*json_candle) for json_candle in json.loads(json_str)["data"]]

    def list(self):
        return [file for file in os.listdir(self.__archive_folder__) if file not in [".", ".."]]

    def get_file_names_filtered(self,
                                exchange_code: str = None,
                                symbol: str = None,
                                data_type: str = None,
                                data_frame: str = None):
        file_names = self.list()
        if exchange_code is not None:
            file_names = [file for file in file_names if file.startswith(f"{exchange_code}_")]

        if symbol is not None:
            file_names = [file for file in file_names if file.split("_")[2] == symbol]

        if data_type is not None:
            file_names = [file for file in file_names if file.split("_")[1] == data_type]

        if data_frame is not None: # there could be several type of file format
            file_names = [file for file in file_names if file.split("_")[3].startswith(data_frame)]

        return file_names

    def read_file(self, file_name):
        with gzip.open(file_name, "r") as f_in:
            json_str = f_in.read().decode(self.__default_encoding__)
        return [Candle.read_json(json_candle) for json_candle in json.loads(json_str)]
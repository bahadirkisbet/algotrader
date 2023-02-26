import configparser
import json
import logging
import os
import gzip

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
             data: list):

        file_name = f"{self.__archive_folder__}/{exchange_code}_{data_type}_{symbol}_{data_frame}.json.gz"
        json_str = json.dumps([candle.get_json() for candle in data]).encode(self.__default_encoding__)
        with gzip.open(file_name, "w") as out:
            out.write(json_str)

    def read(self, exchange_code: str,
             symbol: str,
             data_type: str,
             data_frame: str):
        file_name = f"{self.__archive_folder__}/{exchange_code}_{data_type}_{symbol}_{data_frame}.json.gz"
        with gzip.open(file_name, "r") as f_in:
            json_str = f_in.read().decode(self.__default_encoding__)
        return [Candle.read_json(json_candle) for json_candle in json.loads(json_str)]

    def list(self):
        return [file for file in os.listdir(self.__archive_folder__) if file not in [".", ".."]]

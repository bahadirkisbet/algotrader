from utils.singleton_metaclass.singleton import Singleton
import configparser


class ConfigManager:
    __config__: configparser.ConfigParser = None

    @staticmethod
    def get_config(path=None) -> configparser.ConfigParser:
        if ConfigManager.__config__ is None:
            ConfigManager.__config__ = configparser.ConfigParser()
            ConfigManager.__config__.read("config.ini" if path is None else path)
        return ConfigManager.__config__

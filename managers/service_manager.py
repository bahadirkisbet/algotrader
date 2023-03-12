from managers.archive_manager import ArchiveManager
from managers.config_manager import ConfigManager
from managers.log_manager import LogManager


class ServiceManager:
    __services__: dict = {}

    @staticmethod
    def add_service(name, Service):
        ServiceManager.__services__[name] = Service

    @staticmethod
    def get_service(name):
        try:
            return ServiceManager.__services__[name]
        except KeyError:
            raise KeyError(f"Service {name} is not initialized yet.")

    @staticmethod
    def initialize_logger():
        ServiceManager.add_service("logger", LogManager.get_logger(ConfigManager.get_config()))

    @staticmethod
    def initialize_config():
        ServiceManager.add_service("config", ConfigManager.get_config())

    @staticmethod
    def initialize_archiver():
        logger = ServiceManager.get_service("logger")
        config = ServiceManager.get_service("config")
        ServiceManager.add_service("archiver", ArchiveManager(logger, config))

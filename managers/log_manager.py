import configparser
import logging


class LogManager:
    __logger__: logging.Logger = None

    @staticmethod
    def get_logger(config) -> logging.Logger:
        if LogManager.__logger__ is None:
            LogManager.__logger__ = LogManager.__logger_setup__(config)
        return LogManager.__logger__

    @staticmethod
    def __logger_setup__(config: configparser.ConfigParser) -> logging.Logger:
        # determine logger level from the config
        logging_level = LogManager.__config_logging_level__(config)

        # create logger
        logger: logging.Logger = logging.getLogger(__name__)
        logger.setLevel(logging_level)

        file_handler = logging.FileHandler(config["DEFAULT"]["log_file"], mode="w")

        # create console handler and set level to debug
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging_level)

        # create formatter
        formatter = logging.Formatter('[%(asctime)s] - %(levelname)s \t- %(message)s')

        # add formatter to console handler
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # add ch to logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        logger.info("Logger setup complete")

        return logger

    @staticmethod
    def __config_logging_level__(config: configparser.ConfigParser):
        match config["DEFAULT"]["log_level"]:
            case "debug":
                return logging.DEBUG
            case "info":
                return logging.INFO
            case "warning":
                return logging.WARNING
            case "error":
                return logging.ERROR
            case "critical":
                return logging.CRITICAL
            case _:
                return logging.NOTSET

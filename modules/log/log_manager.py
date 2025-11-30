"""
Log Manager Module

Provides centralized logging configuration and management for the application.
Handles logger setup, file rotation, and console/file output with a simple
singleton pattern.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

from modules.config import config


class LogManager:
    """Log manager for the application."""

    _logger: Optional[logging.Logger] = None

    @classmethod
    def get_logger(cls) -> logging.Logger:
        """Get logger instance."""
        if cls._logger is None:
            cls._logger = cls.setup_logger()
        return cls._logger

    @classmethod
    def setup_logger(cls) -> logging.Logger:
        """Setup logger."""

        cfg = config.get("logging")

        # Determine logger level from the config
        logging_level = cls.get_logging_level(cfg.get("log_level", "info"))

        # Create logger
        logger: logging.Logger = logging.getLogger(__name__)
        logger.setLevel(logging_level)

        # Ensure log directory exists
        log_file = cfg.get("log_file", "log/app.log")
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Create rotating file handler with proper configuration
        max_bytes = int(cfg.get("max_log_size", 10 * 1024 * 1024))
        backup_count = int(cfg.get("log_backup_count", 5))

        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )

        # Create console handler and set level to debug
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging_level)

        # Create formatter with more context
        formatter = logging.Formatter(
            "[%(asctime)s] - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )

        # Add formatter to handlers
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # Add handlers to logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        # Prevent duplicate log messages
        logger.propagate = False

        logger.info("Logger setup complete")

        return logger

    @staticmethod
    def get_logging_level(log_level: str) -> int:
        """Get logging level from config."""
        log_level = log_level.upper()

        return getattr(logging, log_level)

    @classmethod
    def shutdown(cls):
        """Shutdown the log manager gracefully."""
        if cls._logger:
            # Remove all handlers
            for handler in cls._logger.handlers[:]:
                cls._logger.removeHandler(handler)
            cls._logger = None

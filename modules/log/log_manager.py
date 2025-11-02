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

from modules.config.config_manager import ConfigManager


class LogManager:
    """Log manager for the application."""

    _logger: Optional[logging.Logger] = None

    @classmethod
    def get_logger(cls, config: ConfigManager) -> logging.Logger:
        """Get logger instance."""
        if cls._logger is None:
            cls._logger = cls.setup_logger(config)
        return cls._logger

    @classmethod
    def setup_logger(cls, config: ConfigManager) -> logging.Logger:
        """Setup logger."""
        # Determine logger level from the config
        logging_level = cls.get_logging_level(config)

        # Create logger
        logger: logging.Logger = logging.getLogger(__name__)
        logger.setLevel(logging_level)

        # Ensure log directory exists
        log_file = config["DEFAULT"]["log_file"]
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Create rotating file handler with proper configuration
        max_bytes = int(
            config.get("DEFAULT", "max_log_size", fallback=10 * 1024 * 1024)
        )  # 10MB default
        backup_count = int(config.get("DEFAULT", "log_backup_count", fallback=5))

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
    def get_logging_level(config: ConfigManager) -> int:
        """Get logging level from config using if-elif for compatibility."""
        log_level = config.get_value("DEFAULT", "log_level").lower()

        return getattr(logging, log_level)

    @classmethod
    def shutdown(cls):
        """Shutdown the log manager gracefully."""
        if cls._logger:
            # Remove all handlers
            for handler in cls._logger.handlers[:]:
                cls._logger.removeHandler(handler)
            cls._logger = None


# Backward compatibility alias
AsyncLogManager = LogManager

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

from modules.config.config_manager import get_config


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
        # Get global config
        config = get_config()
        
        # Determine logger level from the config
        logging_level = cls.get_logging_level()

        # Create logger
        logger: logging.Logger = logging.getLogger(__name__)
        logger.setLevel(logging_level)

        # Ensure log directory exists
        log_file = config.default.log_file
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Create rotating file handler with proper configuration
        max_bytes = config.default.max_log_size
        backup_count = config.default.log_backup_count

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
    def get_logging_level() -> int:
        """Get logging level from config."""
        config = get_config()
        log_level = config.default.log_level.upper()

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

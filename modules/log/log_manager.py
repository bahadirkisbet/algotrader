import asyncio
import configparser
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional


class LogManager:
    """Log manager for the application."""
    
    _logger: Optional[logging.Logger] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_logger(cls, config) -> logging.Logger:
        """Get logger instance asynchronously."""
        if cls._logger is None:
            async with cls._lock:
                if cls._logger is None:  # Double-check pattern
                    cls._logger = await cls.setup_logger(config)
        return cls._logger

    @classmethod
    async def setup_logger(cls, config: configparser.ConfigParser) -> logging.Logger:
        """Setup logger asynchronously."""
        # Determine logger level from the config
        logging_level = cls.get_logging_level(config)

        # Create logger
        logger: logging.Logger = logging.getLogger(__name__)
        logger.setLevel(logging_level)

        # Ensure log directory exists
        log_file = config["DEFAULT"]["log_file"]
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            # Use asyncio executor for file system operations
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, os.makedirs, log_dir, True)

        # Create rotating file handler with proper configuration
        max_bytes = int(config.get("DEFAULT", "max_log_size", fallback=10 * 1024 * 1024))  # 10MB default
        backup_count = int(config.get("DEFAULT", "log_backup_count", fallback=5))
        
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=max_bytes, 
            backupCount=backup_count,
            encoding='utf-8'
        )

        # Create console handler and set level to debug
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging_level)

        # Create formatter with more context
        formatter = logging.Formatter(
            '[%(asctime)s] - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
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
    def get_logging_level(config: configparser.ConfigParser) -> int:
        """Get logging level from config using if-elif for compatibility."""
        log_level = config["DEFAULT"]["log_level"].lower()
        
        if log_level == "debug":
            return logging.DEBUG
        elif log_level == "info":
            return logging.INFO
        elif log_level == "warning":
            return logging.WARNING
        elif log_level == "error":
            return logging.ERROR
        elif log_level == "critical":
            return logging.CRITICAL
        else:
            return logging.NOTSET

    @classmethod
    async def shutdown(cls):
        """Shutdown the log manager gracefully."""
        if cls._logger:
            # Remove all handlers
            for handler in cls._logger.handlers[:]:
                cls._logger.removeHandler(handler)
            cls._logger = None


# Backward compatibility alias
AsyncLogManager = LogManager

"""
Service Initializer

Handles initialization and shutdown of core application services using the DI container.
"""

import configparser
import logging
from contextlib import asynccontextmanager

from modules.archive.archive_manager import ArchiveManager
from modules.config.async_config_manager import AsyncConfigManager
from modules.log.log_manager import AsyncLogManager
from utils.di_container import get_container, register, register_singleton


class ServiceInitializer:
    """Handles initialization and shutdown of core application services."""
    
    @staticmethod
    async def initialize_logger() -> None:
        """Initialize the logger service."""
        # Get config first
        config = await AsyncConfigManager.get_config()
        
        # Get logger from AsyncLogManager
        logger = await AsyncLogManager.get_logger(config)
        register(logging.Logger, logger)
    
    @staticmethod
    async def initialize_config() -> None:
        """Initialize the configuration service."""
        # Register the AsyncConfigManager as a singleton
        register_singleton(AsyncConfigManager, AsyncConfigManager)
        
        # Also register the configparser.ConfigParser instance
        config = await AsyncConfigManager.get_config()
        register(configparser.ConfigParser, config)
    
    @staticmethod
    async def initialize_archiver() -> None:
        """Initialize the archiver service."""
        archiver = ArchiveManager()
        register_singleton(ArchiveManager, archiver)
    
    @staticmethod
    async def initialize_all() -> None:
        """Initialize all core services."""
        await ServiceInitializer.initialize_logger()
        await ServiceInitializer.initialize_config()
        await ServiceInitializer.initialize_archiver()
    
    @staticmethod
    async def shutdown() -> None:
        """Shutdown all services."""
        container = get_container()
        await container.shutdown()


# Global helper functions
async def initialize_services() -> None:
    """Initialize all services."""
    await ServiceInitializer.initialize_all()


async def shutdown_services() -> None:
    """Shutdown all services."""
    await ServiceInitializer.shutdown()


@asynccontextmanager
async def service_lifecycle():
    """Context manager for service lifecycle."""
    try:
        await initialize_services()
        yield
    finally:
        await shutdown_services() 
"""
Service Initializer

Handles the initialization of core application services using the DI container.
This replaces the ServiceManager's initialization logic with cleaner, more direct code.
"""

import logging
import configparser
from typing import Optional

from .di_container import get_container, register, register_factory
from modules.log.log_manager import LogManager
from modules.archive.archive_manager import ArchiveManager
from managers.config_manager import ConfigManager


class ServiceInitializer:
    """Handles initialization of core application services."""
    
    def __init__(self):
        self.container = get_container()
        self.logger: Optional[logging.Logger] = None
    
    async def initialize_logger(self) -> None:
        """Initialize the logger service."""
        try:
            # Get config first
            config = ConfigManager.get_config()
            
            # Create logger
            logger = LogManager.get_logger(config)
            
            # Register logger in container
            register(logging.Logger, logger)
            self.container.set_logger(logger)
            self.logger = logger
            
            logger.info("Logger service initialized successfully")
            
        except Exception as e:
            # Fallback to basic logging if custom logger fails
            logging.basicConfig(level=logging.INFO)
            fallback_logger = logging.getLogger(__name__)
            fallback_logger.error(f"Failed to initialize custom logger: {e}")
            
            # Register fallback logger
            register(logging.Logger, fallback_logger)
            self.container.set_logger(fallback_logger)
            self.logger = fallback_logger
    
    async def initialize_config(self) -> None:
        """Initialize the configuration service."""
        try:
            config = ConfigManager.get_config()
            register(configparser.ConfigParser, config)
            
            if self.logger:
                self.logger.info("Configuration service initialized successfully")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize configuration: {e}")
            raise
    
    async def initialize_archiver(self) -> None:
        """Initialize the archiver service."""
        try:
            logger = self.container.get(logging.Logger)
            config = self.container.get(configparser.ConfigParser)
            
            archiver = ArchiveManager(logger, config)
            register(ArchiveManager, archiver)
            
            if self.logger:
                self.logger.info("Archiver service initialized successfully")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize archiver: {e}")
            raise
    
    async def initialize_all(self) -> None:
        """Initialize all services in the correct dependency order."""
        try:
            # Initialize services in dependency order
            await self.initialize_logger()
            await self.initialize_config()
            await self.initialize_archiver()
            
            if self.logger:
                self.logger.info("All services initialized successfully")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize services: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown all services gracefully."""
        try:
            if self.logger:
                self.logger.info("Shutting down all services...")
            
            # Shutdown the container
            await self.container.shutdown()
            
            if self.logger:
                self.logger.info("All services shut down successfully")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error during service shutdown: {e}")
            raise


# Global service initializer instance
service_initializer = ServiceInitializer()


async def initialize_services() -> None:
    """Initialize all services using the global service initializer."""
    await service_initializer.initialize_all()


async def shutdown_services() -> None:
    """Shutdown all services using the global service initializer."""
    await service_initializer.shutdown() 
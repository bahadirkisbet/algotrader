import logging
import sys

from modules.websocket.websocket_manager import WebSocketManager
from utils.service_initializer import initialize_services, shutdown_services
from utils.dependency_injection_container import get_container


async def initialize_all_services():
    """Initialize all required services with proper error handling."""
    try:
        # Initialize core services (config, logger, archiver)
        await initialize_services()
        
        # Initialize websocket manager
        await WebSocketManager.initialize()
        
        logging.getLogger(__name__).info("All services initialized successfully")
        
    except Exception as e:
        logging.error(f"Failed to initialize services: {e}")
        sys.exit(1)


async def shutdown_all_services():
    """Shutdown all services gracefully."""
    try:
        await WebSocketManager.close()
        await shutdown_services()
        logging.getLogger(__name__).info("All services shut down successfully")
    except Exception as e:
        logging.error(f"Error during service shutdown: {e}")
        sys.exit(1)


# Global dependency injection container instance
container = get_container() 
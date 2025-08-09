import logging
import sys

from algotrader.modules.websocket.async_websocket_manager import AsyncWebsocketManager

from utils.di_container import get_container


async def inject_services():
    """Initialize all required async services with proper error handling."""
    try:
        # Get the DI container
        container = get_container()
        
        # Initialize async websocket manager
        await AsyncWebsocketManager.initialize()
        
        logging.getLogger(__name__).info("All async services initialized successfully")
        
    except Exception as e:
        logging.error(f"Failed to initialize async services: {e}")
        sys.exit(1)


async def shutdown_services():
    """Shutdown all async services gracefully."""
    try:
        await AsyncWebsocketManager.close()
        logging.getLogger(__name__).info("All async services shut down successfully")
    except Exception as e:
        logging.error(f"Error during async service shutdown: {e}")
        sys.exit(1)


# Global DI container instance
container = get_container() 
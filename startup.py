import asyncio
import logging
import sys
from utils.service_initializer import initialize_services, shutdown_services
from algotrader.modules.websocket.async_websocket_manager import AsyncWebsocketManager


async def inject_services():
    """Initialize all required services with proper error handling."""
    try:
        # Initialize all services in the correct order
        await initialize_services()
        
        # Initialize websocket manager
        await AsyncWebsocketManager.initialize()
        
        logging.getLogger(__name__).info("All services initialized successfully")
        
    except Exception as e:
        logging.error(f"Failed to initialize services: {e}")
        sys.exit(1)


async def shutdown_services():
    """Shutdown all services gracefully."""
    try:
        await AsyncWebsocketManager.close()
        await shutdown_services()
        logging.getLogger(__name__).info("All services shut down successfully")
    except Exception as e:
        logging.error(f"Error during service shutdown: {e}")
        sys.exit(1)


import asyncio
import logging
import signal
import sys
from typing import Dict, Optional

from strategy_provider.strategy_center import StrategyCenter

from data_center.async_data_center import AsyncDataCenter
from managers.async_archive_manager import AsyncArchiveManager
from utils.di_container import get_container
from utils.singleton_metaclass.singleton import Singleton


class AsyncAlgoTrader(metaclass=Singleton):
    """Asynchronous algorithmic trading application."""
    
    def __init__(self):
        self.logger = self.__setup_logging__()
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Initialize components
        self.data_center: Optional[AsyncDataCenter] = None
        self.container = None
        self.strategy_center: Optional[StrategyCenter] = None
        self.archive_manager: Optional[AsyncArchiveManager] = None
        
        # Setup signal handlers
        self.__setup_signal_handlers__()
        
    def __setup_logging__(self) -> logging.Logger:
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def __setup_signal_handlers__(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def initialize(self):
        """Initialize the application components."""
        try:
            self.logger.info("Initializing AsyncAlgoTrader...")
            
            # Initialize archive manager
            self.archive_manager = AsyncArchiveManager()
            
            # Initialize data center
            self.data_center = AsyncDataCenter()
            await self.data_center.initialize()
            
            # Get DI container
            self.container = get_container()
            
            # Initialize strategy center
            self.strategy_center = StrategyCenter()
            
            self.logger.info("AsyncAlgoTrader initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AsyncAlgoTrader: {e}")
            raise
    
    async def start(self):
        """Start the application."""
        try:
            if self.running:
                self.logger.warning("Application is already running")
                return
            
            self.logger.info("Starting AsyncAlgoTrader...")
            self.running = True
            
            # Start data center
            if self.data_center:
                await self.data_center.start()
            
            # Start service manager
            # The service_manager is now managed by the DI container
            # if self.service_manager:
            #     await self.service_manager.start()
            
            # Start strategy center
            if self.strategy_center:
                await self.strategy_center.start()
            
            self.logger.info("AsyncAlgoTrader started successfully")
            
            # Keep running until shutdown is requested
            await self.shutdown_event.wait()
            
        except Exception as e:
            self.logger.error(f"Error starting AsyncAlgoTrader: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the application gracefully."""
        if not self.running:
            return
        
        self.logger.info("Shutting down AsyncAlgoTrader...")
        self.running = False
        self.shutdown_event.set()
        
        try:
            # Shutdown components in reverse order
            if self.strategy_center:
                await self.strategy_center.shutdown()
            
            # The service_manager is now managed by the DI container
            # if self.service_manager:
            #     await self.service_manager.shutdown()
            
            if self.data_center:
                await self.data_center.shutdown()
            
            if self.archive_manager:
                await self.archive_manager.shutdown()
            
            self.logger.info("AsyncAlgoTrader shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    async def get_status(self) -> Dict:
        """Get application status."""
        status = {
            "running": self.running,
            "shutdown_requested": self.shutdown_event.is_set()
        }
        
        if self.data_center:
            status["data_center"] = await self.data_center.get_status()
        
        # The service_manager is now managed by the DI container
        # if self.service_manager:
        #     status["service_manager"] = await self.service_manager.get_status()
        
        if self.strategy_center:
            status["strategy_center"] = await self.strategy_center.get_status()
        
        return status


async def main():
    """Main entry point."""
    app = AsyncAlgoTrader()
    
    try:
        await app.initialize()
        await app.start()
    except KeyboardInterrupt:
        app.logger.info("Received keyboard interrupt")
    except Exception as e:
        app.logger.error(f"Application error: {e}")
        sys.exit(1)
    finally:
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main()) 
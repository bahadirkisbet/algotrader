import asyncio
import signal
from typing import Dict, Optional

from modules.archive import ArchiveManager
from modules.config.config_manager import ConfigManager
from modules.data_center import DataCenter
from modules.log.log_manager import LogManager
from modules.strategy.strategy_center import TradingStrategyManager
from startup import shutdown_all_services
from utils.dependency_injection_container import get_container
from utils.singleton_metaclass.singleton import Singleton


class AlgorithmicTrader(metaclass=Singleton):
    """Algorithmic trading application with asynchronous capabilities."""

    def __init__(self):
        self.config = ConfigManager.get_config()
        self.logger = LogManager.get_logger(self.config)
        self.running = False
        self.shutdown_event = asyncio.Event()

        # Initialize components
        self.data_center: Optional[DataCenter] = None
        self.container = None
        self.strategy_center: Optional[TradingStrategyManager] = None
        self.archive_manager: Optional[ArchiveManager] = None

        # Setup signal handlers
        self.setup_signal_handlers()

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            self.logger.info("Received signal %s, initiating shutdown...", signum)
            asyncio.create_task(self.shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def initialize(self):
        """Initialize the application components."""
        try:
            self.logger.info("Initializing AlgorithmicTrader...")

            # Initialize archive manager
            self.archive_manager = ArchiveManager()

            # Initialize data center
            self.data_center = DataCenter()
            await self.data_center.initialize()

            # Add symbols from config (if needed)
            # For now, add default symbols - this can be configurable
            symbols = ConfigManager.get_value("EXCHANGE", "symbols", fallback="BTCUSDT")
            if isinstance(symbols, str):
                symbols = [s.strip() for s in symbols.split(",")]
            for symbol in symbols:
                self.data_center.add_symbol(symbol)

            # Get DI container
            self.container = get_container()

            # Initialize strategy center
            self.strategy_center = TradingStrategyManager()

            self.logger.info("AlgorithmicTrader initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize AlgorithmicTrader: {e}")
            raise

    async def start(self):
        """Start the application."""
        try:
            if self.running:
                self.logger.warning("Application is already running")
                return

            self.logger.info("Starting AlgorithmicTrader...")
            self.running = True

            # Start data center
            if self.data_center:
                await self.data_center.start()

            # Start strategy center
            if self.strategy_center:
                await self.strategy_center.start()

            self.logger.info("AlgorithmicTrader started successfully")

            # Keep running until shutdown is requested
            await self.shutdown_event.wait()

        except Exception as e:
            self.logger.error(f"Failed to start AlgorithmicTrader: {e}")
            raise

    async def shutdown(self):
        """Shutdown the application gracefully."""
        try:
            if not self.running:
                return

            self.logger.info("Shutting down AlgorithmicTrader...")
            self.running = False

            # Stop data center
            if self.data_center:
                await self.data_center.stop()

            # Stop strategy center
            if self.strategy_center:
                await self.strategy_center.stop()

            # Shutdown all services
            await shutdown_all_services()

            # Set shutdown event
            self.shutdown_event.set()

            self.logger.info("AlgorithmicTrader shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            raise

    async def get_status(self) -> Dict:
        """Get the current status of the application."""
        symbol_count = len(self.data_center.symbols) if self.data_center else 0
        return {
            "running": self.running,
            "data_center_running": self.data_center.is_running if self.data_center else False,
            "strategy_center_running": self.strategy_center.is_running
            if self.strategy_center
            else False,
            "symbol_count": symbol_count,
            "container_services": len(self.container._services) if self.container else 0,
        }


async def main():
    """Main entry point for the application."""
    trader = AlgorithmicTrader()

    try:
        await trader.initialize()
        await trader.start()
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt, shutting down...")
    except Exception as e:
        print(f"Application error: {e}")
        raise
    finally:
        await trader.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

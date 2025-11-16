import asyncio
from typing import Optional

from modules.data_center import DataCenter
from modules.log.log_manager import LogManager
from modules.trading.trading_engine import TradingEngine
from utils.signal_handler import setup_signal_handlers
from utils.singleton_metaclass.singleton import Singleton


class AlgorithmicTrader(metaclass=Singleton):
    """Algorithmic trading application with asynchronous capabilities."""

    def __init__(self):
        self.logger = LogManager.get_logger()

        self.shutdown_event = asyncio.Event()

        # Initialize components
        self.data_center: Optional[DataCenter] = None
        self.trading_engine: Optional[TradingEngine] = None

        # Setup signal handlers
        setup_signal_handlers(self.shutdown, self.logger)

    async def initialize(self):
        """Initialize the application components."""
        try:
            self.logger.info("Initializing AlgorithmicTrader...")

            # Initialize data center
            self.data_center = DataCenter()
            await self.data_center.initialize()

            # Initialize strategy center
            self.trading_engine = TradingEngine(self.data_center)

            self.logger.info("AlgorithmicTrader initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize AlgorithmicTrader: {e}")
            raise

    async def start(self):
        """Start the application."""
        try:
            self.logger.info("Starting AlgorithmicTrader...")

            # Start data center
            if self.data_center:
                await self.data_center.start()

            self.logger.info("AlgorithmicTrader started successfully")

            self.trading_engine.run()

            # Keep running until shutdown is requested
            await self.shutdown_event.wait()

        except Exception as e:
            self.logger.error(f"Failed to start AlgorithmicTrader: {e}")
            raise

    async def shutdown(self):
        """Shutdown the application gracefully."""
        try:
            self.logger.info("Shutting down AlgorithmicTrader...")

            # Stop data center
            await self.data_center.stop()

            # Stop trading engine
            await self.trading_engine.stop()

            self.logger.info("AlgorithmicTrader shutdown complete")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            raise


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

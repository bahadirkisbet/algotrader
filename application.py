import asyncio
import signal
import sys
import configparser
from models.exchange_type import ExchangeType
from data_center.async_data_center import AsyncDataCenter
from data_provider.exchange_collection.exchange_factory import ExchangeFactory
from startup import inject_services, shutdown_services
from utils.di_container import get, register


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print(f"\nReceived signal {signum}, shutting down gracefully...")
    asyncio.create_task(shutdown_services())


async def main():
    """Main application entry point with proper error handling."""
    try:
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        print("Starting AlgoTrader...")
        
        # Initialize all services
        await inject_services()
        
        # Get configuration
        config = get(configparser.ConfigParser)
        exchange_name = config["EXCHANGE"]["exchange_code"]
        
        # Create exchange instance
        exchange = ExchangeFactory.create(exchange_name, ExchangeType.SPOT)
        register(type(exchange), exchange)
        
        print(f"Connected to exchange: {exchange_name}")
        
        # Create and start data center
        data_center = AsyncDataCenter()
        await data_center.start()
        
        print("AlgoTrader is running. Press Ctrl+C to exit gracefully.")
        
        # Keep the main event loop alive
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nShutdown requested by user...")
        
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        # Ensure cleanup happens
        try:
            await shutdown_services()
        except Exception as e:
            print(f"Error during shutdown: {e}")
        print("AlgoTrader shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())

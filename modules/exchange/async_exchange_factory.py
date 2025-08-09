import logging
from typing import Dict, Optional, Type

from data_provider.exchange_collection.async_binance_exchange import AsyncBinanceExchange
from modules.exchange.exchange_interface import ExchangeInterface

from models.exchange_type import ExchangeType


class AsyncExchangeFactory:
    """Factory for creating async exchange instances."""

    __exchanges__: Dict[str, Type[ExchangeInterface]] = {}
    __logger__: Optional[logging.Logger] = None

    @classmethod
    def __init__(cls):
        """Initialize the factory with available exchanges."""
        cls.__register_exchanges__()

    @classmethod
    def __register_exchanges__(cls):
        """Register all available exchange implementations."""
        cls.__exchanges__ = {
            "BNB": AsyncBinanceExchange,  # Binance
            "BINANCE": AsyncBinanceExchange,  # Alternative name
            # Add more exchanges here as they are implemented
        }

    @classmethod
    async def create(cls, exchange_code: str, exchange_type: ExchangeType) -> ExchangeInterface:
        """Create an async exchange instance."""
        try:
            if exchange_code not in cls.__exchanges__:
                raise ValueError(f"Unsupported exchange: {exchange_code}")

            exchange_class = cls.__exchanges__[exchange_code]
            exchange = exchange_class(exchange_type)
            
            # Initialize the exchange
            await exchange.initialize()
            
            if cls.__logger__:
                cls.__logger__.info(f"Created async exchange: {exchange_code} ({exchange_type.value})")
            
            return exchange

        except Exception as e:
            if cls.__logger__:
                cls.__logger__.error(f"Failed to create exchange {exchange_code}: {e}")
            raise

    @classmethod
    def get_supported_exchanges(cls) -> list[str]:
        """Get list of supported exchange codes."""
        return list(cls.__exchanges__.keys())

    @classmethod
    def is_supported(cls, exchange_code: str) -> bool:
        """Check if an exchange is supported."""
        return exchange_code in cls.__exchanges__

    @classmethod
    def register_exchange(cls, exchange_code: str, exchange_class: Type[ExchangeInterface]):
        """Register a new exchange implementation."""
        cls.__exchanges__[exchange_code] = exchange_class
        if cls.__logger__:
            cls.__logger__.info(f"Registered new exchange: {exchange_code}")

    @classmethod
    def set_logger(cls, logger: logging.Logger):
        """Set the logger for the factory."""
        cls.__logger__ = logger


# Initialize the factory
AsyncExchangeFactory() 
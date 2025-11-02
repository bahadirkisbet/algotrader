"""
Exchange Factory for creating exchange instances.

This module provides a factory for creating exchange and websocket instances,
following the Factory design pattern and SOLID principles.
"""

from models.exchange_type import ExchangeType
from modules.exchange.exchange import Exchange
from modules.exchange.exchange_library.binance.binance import BinanceExchange
from modules.exchange.exchange_library.binance.binance_ws import BinanceWebSocket
from modules.exchange.exchange_websocket import ExchangeWebSocket


class ExchangeFactory:
    """
    Factory class for creating exchange instances.

    This factory follows the Open/Closed Principle by making it easy to add
    new exchanges without modifying existing code.
    """

    # Registry of available exchanges
    _exchange_registry = {
        "BNB": BinanceExchange,
        "BINANCE": BinanceExchange,
    }

    # Registry of available WebSocket implementations
    _websocket_registry = {
        "BNB": BinanceWebSocket,
        "BINANCE": BinanceWebSocket,
    }

    @classmethod
    async def create_exchange(
        cls, exchange_code: str, exchange_type: ExchangeType = ExchangeType.SPOT
    ) -> Exchange:
        """
        Create an exchange instance.

        Args:
            exchange_code: Exchange identifier (e.g., "BNB", "BINANCE")
            exchange_type: Type of exchange (SPOT, FUTURES, etc.)

        Returns:
            Initialized Exchange instance

        Raises:
            ValueError: If exchange is not supported
        """
        exchange_code_upper = exchange_code.upper()

        if exchange_code_upper not in cls._exchange_registry:
            raise ValueError(
                f"Unsupported exchange: {exchange_code}. "
                f"Supported exchanges: {list(cls._exchange_registry.keys())}"
            )

        exchange_class = cls._exchange_registry[exchange_code_upper]
        exchange = exchange_class(exchange_type)

        # Initialize the exchange
        await exchange.initialize()

        return exchange

    @classmethod
    def create_websocket(cls, exchange_code: str) -> ExchangeWebSocket:
        """
        Create a WebSocket instance for an exchange.

        Args:
            exchange_code: Exchange identifier (e.g., "BNB", "BINANCE")

        Returns:
            ExchangeWebSocket instance

        Raises:
            ValueError: If exchange WebSocket is not supported
        """
        exchange_code_upper = exchange_code.upper()

        if exchange_code_upper not in cls._websocket_registry:
            raise ValueError(
                f"Unsupported exchange WebSocket: {exchange_code}. "
                f"Supported exchanges: {list(cls._websocket_registry.keys())}"
            )

        websocket_class = cls._websocket_registry[exchange_code_upper]
        return websocket_class()

    @classmethod
    def get_supported_exchanges(cls) -> list:
        """
        Get list of supported exchange codes.

        Returns:
            List of exchange codes
        """
        return list(cls._exchange_registry.keys())

    @classmethod
    def is_supported(cls, exchange_code: str) -> bool:
        """
        Check if an exchange is supported.

        Args:
            exchange_code: Exchange identifier

        Returns:
            True if supported, False otherwise
        """
        return exchange_code.upper() in cls._exchange_registry

    # Legacy compatibility method
    @classmethod
    async def create(
        cls, exchange_name: str, exchange_type: ExchangeType = ExchangeType.SPOT
    ) -> Exchange:
        """
        Create an exchange instance (legacy compatibility).

        Args:
            exchange_name: Exchange identifier
            exchange_type: Type of exchange

        Returns:
            Initialized Exchange instance
        """
        return await cls.create_exchange(exchange_name, exchange_type)

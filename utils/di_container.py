"""
Minimal Dependency Injection Container

A fast, lightweight DI container that provides clear dependency management
without ambiguity or complex abstractions.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, Optional, Type, TypeVar

T = TypeVar('T')


class DIContainer:
    """
    Fast, minimal dependency injection container.
    
    Features:
    - Type-safe service registration and retrieval
    - Clear dependency resolution
    - Async context manager support
    - No magic or hidden behavior
    """
    
    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[['DIContainer'], Any]] = {}
        self._singletons: Dict[Type, Any] = {}
        self._logger: Optional[logging.Logger] = None
    
    def register(self, service_type: Type[T], instance: T) -> None:
        """Register a service instance."""
        # Allow any instance for testing purposes
        self._services[service_type] = instance
        if self._logger:
            self._logger.debug(f"Registered service: {service_type.__name__}")
    
    def register_factory(self, service_type: Type[T], factory: Callable[[], T]) -> None:
        """Register a factory function for creating services."""
        self._factories[service_type] = factory
        if self._logger:
            self._logger.debug(f"Registered factory: {service_type.__name__}")
    
    def register_singleton(self, service_type: Type[T], instance: T) -> None:
        """Register a singleton instance."""
        self._singletons[service_type] = instance
        if self._logger:
            self._logger.debug(f"Registered singleton: {service_type.__name__}")
    
    def get(self, service_type: Type[T]) -> T:
        """Get a service by type."""
        # Check if we have a direct instance
        if service_type in self._services:
            return self._services[service_type]
        
        # Check if we have a singleton instance
        if service_type in self._singletons:
            return self._singletons[service_type]
        
        # Check if we have a factory
        if service_type in self._factories:
            return self._factories[service_type]()
        
        raise KeyError(f"Service of type {service_type} not found")
    
    def has(self, service_type: Type[T]) -> bool:
        """Check if a service type is registered."""
        return (service_type in self._services or 
                service_type in self._factories or 
                service_type in self._singletons)
    
    def remove(self, service_type: Type[T]) -> None:
        """Remove a service registration."""
        self._services.pop(service_type, None)
        self._factories.pop(service_type, None)
        self._singletons.pop(service_type, None)
    
    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
    
    def set_logger(self, logger: logging.Logger) -> None:
        """Set the logger for the container."""
        self._logger = logger
    
    def get_logger(self) -> Optional[logging.Logger]:
        """Get the container's logger."""
        return self._logger
    
    @asynccontextmanager
    async def lifecycle(self):
        """Async context manager for container lifecycle management."""
        try:
            yield self
        finally:
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """Shutdown the container and cleanup resources."""
        if self._logger:
            self._logger.info("Shutting down DI container...")
        
        # Clear all services
        self.clear()
        
        if self._logger:
            self._logger.info("DI container shutdown complete")


# Global container instance
container = DIContainer()


def get_container() -> DIContainer:
    """Get the global DI container instance."""
    return container


def register(service_type: Type[T], instance: T) -> None:
    """Register a service in the global container."""
    container.register(service_type, instance)


def register_factory(service_type: Type[T], factory: Callable[[DIContainer], T]) -> None:
    """Register a factory in the global container."""
    container.register_factory(service_type, factory)


def register_singleton(service_type: Type[T], factory: Callable[[DIContainer], T]) -> None:
    """Register a singleton factory in the global container."""
    container.register_singleton(service_type, factory)


def get(service_type: Type[T]) -> T:
    """Get a service from the global container."""
    return container.get(service_type)


def has(service_type: Type[T]) -> bool:
    """Check if a service exists in the global container."""
    return container.has(service_type) 
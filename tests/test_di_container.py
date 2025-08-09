"""
Tests for the new DI container that replaces ServiceManager.
"""

import pytest
import logging
import configparser
from unittest.mock import Mock, MagicMock

from utils.di_container import DIContainer, get, register, has


class TestDIContainer:
    """Test the DI container functionality."""
    
    def test_register_and_get_service(self):
        """Test basic service registration and retrieval."""
        container = DIContainer()
        
        # Create a mock service
        mock_service = Mock()
        mock_service.name = "test_service"
        
        # Register the service
        container.register(Mock, mock_service)
        
        # Retrieve the service
        retrieved_service = container.get(Mock)
        
        assert retrieved_service is mock_service
        assert retrieved_service.name == "test_service"
    
    def test_register_factory(self):
        """Test factory registration and usage."""
        container = DIContainer()
        
        # Create a factory function
        def create_service(container):
            service = Mock()
            service.name = "factory_service"
            return service
        
        # Register the factory
        container.register_factory(Mock, create_service)
        
        # Get the service (should be created by factory)
        service = container.get(Mock)
        
        assert service.name == "factory_service"
    
    def test_register_singleton(self):
        """Test singleton registration and usage."""
        container = DIContainer()
        
        # Create a factory function
        def create_singleton(container):
            service = Mock()
            service.name = "singleton_service"
            return service
        
        # Register the singleton factory
        container.register_singleton(Mock, create_singleton)
        
        # Get the service twice
        service1 = container.get(Mock)
        service2 = container.get(Mock)
        
        # Both should be the same instance
        assert service1 is service2
        assert service1.name == "singleton_service"
    
    def test_has_service(self):
        """Test service existence checking."""
        container = DIContainer()
        
        # Initially no services
        assert not container.has(Mock)
        
        # Register a service
        mock_service = Mock()
        container.register(Mock, mock_service)
        
        # Now should have the service
        assert container.has(Mock)
    
    def test_remove_service(self):
        """Test service removal."""
        container = DIContainer()
        
        # Register a service
        mock_service = Mock()
        container.register(Mock, mock_service)
        assert container.has(Mock)
        
        # Remove the service
        container.remove(Mock)
        assert not container.has(Mock)
    
    def test_clear_services(self):
        """Test clearing all services."""
        container = DIContainer()
        
        # Register multiple services
        container.register(Mock, Mock())
        container.register(str, "test")
        
        assert container.has(Mock)
        assert container.has(str)
        
        # Clear all services
        container.clear()
        
        assert not container.has(Mock)
        assert not container.has(str)
    
    def test_type_safety(self):
        """Test that type safety is enforced."""
        container = DIContainer()
        
        # Try to register wrong type
        with pytest.raises(TypeError):
            container.register(str, 42)  # int is not a string
    
    def test_service_not_found(self):
        """Test error when service is not found."""
        container = DIContainer()
        
        with pytest.raises(KeyError):
            container.get(Mock)
    
    def test_global_functions(self):
        """Test the global convenience functions."""
        # Test register and get
        mock_service = Mock()
        register(Mock, mock_service)
        
        retrieved_service = get(Mock)
        assert retrieved_service is mock_service
        
        # Test has
        assert has(Mock)
        assert not has(str)


class TestServiceInitializer:
    """Test the service initializer that replaces ServiceManager initialization."""
    
    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test that services can be initialized properly."""
        from utils.service_initializer import ServiceInitializer
        
        # Mock the dependencies
        with pytest.patch('managers.config_manager.ConfigManager.get_config') as mock_get_config, \
             pytest.patch('algotrader.modules.log.log_manager.LogManager.get_logger') as mock_get_logger, \
             pytest.patch('algotrader.modules.archive.archive_manager.ArchiveManager') as mock_archive_manager:
            
            # Setup mocks
            mock_config = MagicMock(spec=configparser.ConfigParser)
            mock_logger = MagicMock(spec=logging.Logger)
            mock_archive = MagicMock()
            
            mock_get_config.return_value = mock_config
            mock_get_logger.return_value = mock_logger
            mock_archive_manager.return_value = mock_archive
            
            # Create initializer and initialize services
            initializer = ServiceInitializer()
            await initializer.initialize_all()
            
            # Verify that services were registered
            from utils.di_container import get, has
            
            assert has(logging.Logger)
            assert has(configparser.ConfigParser)
            assert has(type(mock_archive))
            
            # Verify logger was set
            assert initializer.logger is mock_logger 
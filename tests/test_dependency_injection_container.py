"""
Tests for the DI Container and Service Initializer.
"""

from unittest.mock import MagicMock, patch

import pytest

from utils.dependency_injection_container import (
    DependencyInjectionContainer,
    get,
    get_container,
    has,
    register,
    register_factory,
    register_singleton,
)


class TestDependencyInjectionContainer:
    """Test the DependencyInjectionContainer class."""
    
    def test_register_and_get_service(self):
        """Test registering and getting a service."""
        container = DependencyInjectionContainer()
        mock_service = MagicMock()
        
        container.register(str, mock_service)
        result = container.get(str)
        
        assert result is mock_service
    
    def test_register_factory(self):
        """Test registering a factory function."""
        container = DependencyInjectionContainer()
        
        def factory():
            return "created"
        
        container.register_factory(str, factory)
        result = container.get(str)
        
        assert result == "created"
    
    def test_register_singleton(self):
        """Test registering a singleton."""
        container = DependencyInjectionContainer()
        mock_service = MagicMock()
        
        container.register_singleton(str, mock_service)
        result1 = container.get(str)
        result2 = container.get(str)
        
        assert result1 is result2
        assert result1 is mock_service
    
    def test_has_service(self):
        """Test checking if a service exists."""
        container = DependencyInjectionContainer()
        
        assert not container.has(str)
        
        container.register(str, "test")
        assert container.has(str)
    
    def test_remove_service(self):
        """Test removing a service."""
        container = DependencyInjectionContainer()
        container.register(str, "test")
        
        assert container.has(str)
        container.remove(str)
        assert not container.has(str)
    
    def test_clear_services(self):
        """Test clearing all services."""
        container = DependencyInjectionContainer()
        container.register(str, "test")
        container.register(int, 42)
        
        assert container.has(str)
        assert container.has(int)
        
        container.clear()
        assert not container.has(str)
        assert not container.has(int)
    
    def test_type_safety(self):
        """Test that type safety is maintained."""
        container = DependencyInjectionContainer()
        
        # Should work with same type
        container.register(str, "test")
        result = container.get(str)
        assert isinstance(result, str)
        
        # Should not work with different type
        with pytest.raises(KeyError):
            container.get(int)
    
    def test_service_not_found(self):
        """Test getting a non-existent service."""
        container = DIContainer()
        
        with pytest.raises(KeyError):
            container.get(str)
    
    def test_global_functions(self):
        """Test the global helper functions."""
        # Test global container
        container1 = get_container()
        container2 = get_container()
        assert container1 is container2
        
        # Test global register
        register(str, "test")
        assert get(str) == "test"
        assert has(str)
        
        # Test global register_factory
        def factory():
            return "factory_result"
        register_factory(int, factory)
        assert get(int) == "factory_result"
        
        # Test global register_singleton
        register_singleton(float, 3.14)
        assert get(float) == 3.14
        
        # Clean up
        container1.clear()


class TestServiceInitializer:
    """Test the ServiceInitializer class."""
    
    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test that services can be initialized properly."""
        from utils.service_initializer import ServiceInitializer
        
        # Mock the dependencies
        with patch('modules.config.async_config_manager.AsyncConfigManager.get_config') as mock_get_config, \
             patch('modules.log.log_manager.AsyncLogManager.get_logger') as mock_get_logger, \
             patch('utils.service_initializer.ArchiveManager') as mock_archive_manager:
            
            # Setup mocks
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config
            
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            mock_archive_instance = MagicMock()
            mock_archive_manager.return_value = mock_archive_instance
            
            # Test initialization
            await ServiceInitializer.initialize_all()
            
            # Verify mocks were called
            mock_get_config.assert_called()
            assert mock_get_config.call_count == 2  # Called in initialize_logger and initialize_config
            mock_get_logger.assert_called_once_with(mock_config)
            mock_archive_manager.assert_called_once() 
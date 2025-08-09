import os
import configparser
from typing import Dict, Any, List, Tuple
from enum import Enum


class ConfigSection(Enum):
    """Configuration sections."""
    DEFAULT = "DEFAULT"
    EXCHANGE = "EXCHANGE"
    LOGGING = "LOGGING"


class ConfigValidator:
    """Validates configuration values and provides defaults."""
    
    # Required configuration fields
    REQUIRED_FIELDS = {
        ConfigSection.DEFAULT: ["log_level", "log_file", "development_mode", "archive_folder"],
        ConfigSection.EXCHANGE: ["exchange_code", "subscription_type", "max_connection_limit", "time_frame"],
        ConfigSection.LOGGING: ["enable_console_logging", "enable_file_logging", "log_format"]
    }
    
    # Default values for optional fields
    DEFAULT_VALUES = {
        ConfigSection.DEFAULT: {
            "max_log_size": "10485760",  # 10MB
            "log_backup_count": "5"
        },
        ConfigSection.EXCHANGE: {
            "default_interval": "1m"
        },
        ConfigSection.LOGGING: {
            "enable_console_logging": "true",
            "enable_file_logging": "true",
            "log_format": "detailed"
        }
    }
    
    # Valid values for specific fields
    VALID_VALUES = {
        "log_level": ["debug", "info", "warning", "error", "critical"],
        "development_mode": ["true", "false"],
        "enable_console_logging": ["true", "false"],
        "enable_file_logging": ["true", "false"],
        "log_format": ["simple", "detailed", "json"]
    }
    
    # Field type validators
    FIELD_TYPES = {
        "max_connection_limit": int,
        "max_log_size": int,
        "log_backup_count": int
    }
    
    @classmethod
    def validate_config(cls, config: configparser.ConfigParser) -> Tuple[bool, List[str]]:
        """
        Validate the entire configuration.
        
        Args:
            config: Configuration parser instance
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required sections
        for section in ConfigSection:
            if not config.has_section(section.value):
                errors.append(f"Missing required section: [{section.value}]")
                continue
            
            # Check required fields in section
            for field in cls.REQUIRED_FIELDS[section]:
                if not config.has_option(section.value, field):
                    errors.append(f"Missing required field: [{section.value}].{field}")
        
        # Validate field values
        for section in ConfigSection:
            if config.has_section(section.value):
                for field, value in config.items(section.value):
                    field_errors = cls._validate_field(section.value, field, value)
                    errors.extend(field_errors)
        
        return len(errors) == 0, errors
    
    @classmethod
    def _validate_field(cls, section: str, field: str, value: str) -> List[str]:
        """Validate a specific field value."""
        errors = []
        
        # Check if field has valid values
        if field in cls.VALID_VALUES:
            if value.lower() not in cls.VALID_VALUES[field]:
                errors.append(f"Invalid value for [{section}].{field}: '{value}'. "
                            f"Valid values: {cls.VALID_VALUES[field]}")
        
        # Check field type
        if field in cls.FIELD_TYPES:
            try:
                cls.FIELD_TYPES[field](value)
            except ValueError:
                errors.append(f"Invalid type for [{section}].{field}: '{value}' "
                            f"should be {cls.FIELD_TYPES[field].__name__}")
        
        # Special validations
        if field == "log_file":
            if not cls._is_valid_log_path(value):
                errors.append(f"Invalid log file path: {value}")
        
        if field == "archive_folder":
            if not cls._is_valid_folder_path(value):
                errors.append(f"Invalid archive folder path: {value}")
        
        if field == "max_connection_limit":
            limit = int(value)
            if limit <= 0 or limit > 10000:
                errors.append(f"Connection limit must be between 1 and 10000, got: {limit}")
        
        if field == "max_log_size":
            size = int(value)
            if size <= 0 or size > 100 * 1024 * 1024:  # 100MB max
                errors.append(f"Log size must be between 1 and 100MB, got: {size}")
        
        if field == "log_backup_count":
            count = int(value)
            if count < 0 or count > 100:
                errors.append(f"Log backup count must be between 0 and 100, got: {count}")
        
        return errors
    
    @staticmethod
    def _is_valid_log_path(path: str) -> bool:
        """Check if log file path is valid."""
        if not path:
            return False
        
        # Check if directory is writable
        log_dir = os.path.dirname(path)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except (OSError, PermissionError):
                return False
        
        return True
    
    @staticmethod
    def _is_valid_folder_path(path: str) -> bool:
        """Check if folder path is valid."""
        if not path:
            return False
        
        # Check if directory exists or can be created
        if not os.path.exists(path):
            try:
                os.makedirs(path, exist_ok=True)
            except (OSError, PermissionError):
                return False
        
        return True
    
    @classmethod
    def apply_defaults(cls, config: configparser.ConfigParser) -> None:
        """Apply default values for missing optional fields."""
        for section, defaults in cls.DEFAULT_VALUES.items():
            if not config.has_section(section.value):
                config.add_section(section.value)
            
            for field, default_value in defaults.items():
                if not config.has_option(section.value, field):
                    config.set(section.value, field, default_value)
    
    @classmethod
    def get_config_summary(cls, config: configparser.ConfigParser) -> Dict[str, Any]:
        """Get a summary of the configuration."""
        summary = {}
        
        for section in ConfigSection:
            if config.has_section(section.value):
                summary[section.value] = dict(config.items(section.value))
        
        return summary
    
    @classmethod
    def create_sample_config(cls) -> str:
        """Create a sample configuration file content."""
        config = configparser.ConfigParser()
        
        # Add sections
        for section in ConfigSection:
            config.add_section(section.value)
        
        # Add required fields with sample values
        config.set(ConfigSection.DEFAULT.value, "log_level", "info")
        config.set(ConfigSection.DEFAULT.value, "log_file", "log/app.log")
        config.set(ConfigSection.DEFAULT.value, "development_mode", "true")
        config.set(ConfigSection.DEFAULT.value, "archive_folder", "archive")
        config.set(ConfigSection.DEFAULT.value, "max_log_size", "10485760")
        config.set(ConfigSection.DEFAULT.value, "log_backup_count", "5")
        
        config.set(ConfigSection.EXCHANGE.value, "exchange_code", "BNB")
        config.set(ConfigSection.EXCHANGE.value, "subscription_type", "CANDLE")
        config.set(ConfigSection.EXCHANGE.value, "max_connection_limit", "100")
        config.set(ConfigSection.EXCHANGE.value, "time_frame", "5m")
        config.set(ConfigSection.EXCHANGE.value, "default_interval", "1m")
        
        config.set(ConfigSection.LOGGING.value, "enable_console_logging", "true")
        config.set(ConfigSection.LOGGING.value, "enable_file_logging", "true")
        config.set(ConfigSection.LOGGING.value, "log_format", "detailed")
        
        # Convert to string
        config_string = []
        for section in config.sections():
            config_string.append(f"[{section}]")
            for key, value in config.items(section):
                config_string.append(f"{key} = {value}")
            config_string.append("")
        
        return "\n".join(config_string) 
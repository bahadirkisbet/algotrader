"""Configuration manager with validation and caching.

This module provides a configuration manager with validation and caching.
It is used to load and validate the configuration file, and to get the configuration values.
"""

import configparser
import os
from typing import Any, Dict, Optional

from .config_validator import ConfigValidator


class ConfigManager:
    """Configuration manager with validation and caching."""

    _config: Optional[configparser.ConfigParser] = None
    _config_file: str = "config.ini"

    @classmethod
    def get_config(cls) -> configparser.ConfigParser:
        """Get the configuration, loading it if needed."""
        if cls._config is None:
            cls._load_config()
        return cls._config

    @classmethod
    def reload_config(cls) -> configparser.ConfigParser:
        """Reload the configuration from file."""
        cls._config = None
        cls._load_config()
        return cls._config

    @classmethod
    def _load_config(cls) -> None:
        """Load configuration from file with validation."""
        try:
            if not os.path.exists(cls._config_file):
                raise FileNotFoundError(f"Configuration file '{cls._config_file}' not found")

            config = configparser.ConfigParser()
            config.read(cls._config_file)

            # Validate and apply defaults
            ConfigValidator.validate_config(config)
            ConfigValidator.apply_defaults(config)

            cls._config = config

        except (FileNotFoundError, configparser.Error, ValueError) as e:
            raise ValueError(f"Failed to load configuration: {e}") from e

    @classmethod
    def get_value(cls, section: str, option: str, fallback: Any = None) -> Any:
        """Get a configuration value with fallback."""
        config = cls.get_config()
        return config.get(section, option, fallback=fallback)

    @classmethod
    def get_int(cls, section: str, option: str, fallback: int = None) -> int:
        """Get an integer configuration value."""
        config = cls.get_config()
        return config.getint(section, option, fallback=fallback)

    @classmethod
    def get_float(cls, section: str, option: str, fallback: float = None) -> float:
        """Get a float configuration value."""
        config = cls.get_config()
        return config.getfloat(section, option, fallback=fallback)

    @classmethod
    def get_boolean(cls, section: str, option: str, fallback: bool = None) -> bool:
        """Get a boolean configuration value."""
        config = cls.get_config()
        return config.getboolean(section, option, fallback=fallback)

    @classmethod
    def has_section(cls, section: str) -> bool:
        """Check if a section exists."""
        config = cls.get_config()
        return config.has_section(section)

    @classmethod
    def has_option(cls, section: str, option: str) -> bool:
        """Check if an option exists in a section."""
        config = cls.get_config()
        return config.has_option(section, option)

    @classmethod
    def get_section(cls, section: str) -> Dict[str, str]:
        """Get all options from a section."""
        config = cls.get_config()
        if not config.has_section(section):
            raise KeyError(f"Section '{section}' not found")
        return dict(config.items(section))

    @classmethod
    def get_config_summary(cls) -> Dict[str, Any]:
        """Get a summary of the current configuration."""
        config = cls.get_config()
        return ConfigValidator.get_config_summary(config)

    @classmethod
    def validate_current_config(cls) -> Dict[str, Any]:
        """Validate the current configuration and return validation results."""
        config = cls.get_config()
        return ConfigValidator.validate_config(config)

    @classmethod
    def create_sample_config(cls, output_file: str = "config_sample.ini") -> str:
        """Create a sample configuration file."""
        content = ConfigValidator.create_sample_config()
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        return content

    @classmethod
    def set_config_file(cls, file_path: str) -> None:
        """Set the configuration file path."""
        cls._config_file = file_path

    @classmethod
    def get_config_file_path(cls) -> str:
        """Get the current configuration file path."""
        return cls._config_file

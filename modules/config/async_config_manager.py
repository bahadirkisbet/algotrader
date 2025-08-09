import asyncio
import configparser
import os
from typing import Any, Dict, Optional

from algotrader.modules.config.config_validator import ConfigValidator


class AsyncConfigManager:
    """Async configuration manager with validation and caching."""

    __config__: Optional[configparser.ConfigParser] = None
    __config_file__: str = "config.ini"
    __lock__ = asyncio.Lock()

    @classmethod
    async def get_config(cls) -> configparser.ConfigParser:
        """Get the configuration, loading it asynchronously if needed."""
        if cls.__config__ is None:
            async with cls.__lock__:
                if cls.__config__ is None:
                    await cls.__load_config__()
        return cls.__config__

    @classmethod
    async def reload_config(cls) -> configparser.ConfigParser:
        """Reload the configuration from file."""
        async with cls.__lock__:
            cls.__config__ = None
            await cls.__load_config__()
        return cls.__config__

    @classmethod
    async def __load_config__(cls) -> None:
        """Load configuration from file with validation."""
        try:
            if not os.path.exists(cls.__config_file__):
                raise FileNotFoundError(f"Configuration file '{cls.__config_file__}' not found")

            config = configparser.ConfigParser()
            config.read(cls.__config_file__)

            # Validate and apply defaults
            ConfigValidator.validate_config(config)
            ConfigValidator.apply_defaults(config)

            cls.__config__ = config

        except Exception as e:
            raise ValueError(f"Failed to load configuration: {e}")

    @classmethod
    async def get_value(cls, section: str, option: str, fallback: Any = None) -> Any:
        """Get a configuration value with fallback."""
        config = await cls.get_config()
        return config.get(section, option, fallback=fallback)

    @classmethod
    async def get_int(cls, section: str, option: str, fallback: int = None) -> int:
        """Get an integer configuration value."""
        config = await cls.get_config()
        return config.getint(section, option, fallback=fallback)

    @classmethod
    async def get_float(cls, section: str, option: str, fallback: float = None) -> float:
        """Get a float configuration value."""
        config = await cls.get_config()
        return config.getfloat(section, option, fallback=fallback)

    @classmethod
    async def get_boolean(cls, section: str, option: str, fallback: bool = None) -> bool:
        """Get a boolean configuration value."""
        config = await cls.get_config()
        return config.getboolean(section, option, fallback=fallback)

    @classmethod
    async def has_section(cls, section: str) -> bool:
        """Check if a section exists."""
        config = await cls.get_config()
        return config.has_section(section)

    @classmethod
    async def has_option(cls, section: str, option: str) -> bool:
        """Check if an option exists in a section."""
        config = await cls.get_config()
        return config.has_option(section, option)

    @classmethod
    async def get_section(cls, section: str) -> Dict[str, str]:
        """Get all options from a section."""
        config = await cls.get_config()
        if not config.has_section(section):
            raise KeyError(f"Section '{section}' not found")
        return dict(config.items(section))

    @classmethod
    async def get_config_summary(cls) -> Dict[str, Any]:
        """Get a summary of the current configuration."""
        config = await cls.get_config()
        return ConfigValidator.get_config_summary(config)

    @classmethod
    async def validate_current_config(cls) -> Dict[str, Any]:
        """Validate the current configuration."""
        config = await cls.get_config()
        return ConfigValidator.validate_config(config)

    @classmethod
    async def create_sample_config(cls, output_file: str = "config_sample.ini") -> str:
        """Create a sample configuration file."""
        return ConfigValidator.create_sample_config(output_file)

    @classmethod
    def set_config_file(cls, file_path: str) -> None:
        """Set the configuration file path."""
        cls.__config_file__ = file_path

    @classmethod
    def get_config_file_path(cls) -> str:
        """Get the current configuration file path."""
        return cls.__config_file__ 
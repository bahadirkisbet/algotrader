"""Configuration manager using Pydantic and environment variables.

This module provides a configuration manager that loads settings from .env file
using Pydantic models for validation. It uses '__' as the nested delimiter for
environment variables.
"""

import os
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DefaultConfig(BaseModel):
    """Default configuration section."""

    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info"
    log_file: str = "log/app.log"
    max_log_size: int = Field(
        default=10485760, ge=1, le=100 * 1024 * 1024
    )  # 10MB default, max 100MB
    log_backup_count: int = Field(default=5, ge=0, le=100)
    development_mode: bool = True
    archive_folder: str = ".cache"

    @field_validator("log_file")
    @classmethod
    def validate_log_file(cls, v: str) -> str:
        """Validate log file path."""
        log_dir = os.path.dirname(v)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except (OSError, PermissionError) as e:
                raise ValueError(f"Cannot create log directory: {e}") from e
        return v

    @field_validator("archive_folder")
    @classmethod
    def validate_archive_folder(cls, v: str) -> str:
        """Validate archive folder path."""
        if not os.path.exists(v):
            try:
                os.makedirs(v, exist_ok=True)
            except (OSError, PermissionError) as e:
                raise ValueError(f"Cannot create archive folder: {e}") from e
        return v


class ExchangeConfig(BaseModel):
    """Exchange configuration section."""

    exchange_code: str = "BNB"
    subscription_type: str = "CANDLE"
    max_connection_limit: int = Field(default=100, ge=1, le=10000)
    time_frame: str = "1h"
    default_interval: str = "1h"
    symbols: Optional[str] = None  # Optional, can be comma-separated


class LoggingConfig(BaseModel):
    """Logging configuration section."""

    enable_console_logging: bool = True
    enable_file_logging: bool = True
    log_format: Literal["simple", "detailed", "json"] = "detailed"


class TradingConfig(BaseModel):
    """Trading configuration section."""

    engine_type: str = "BACKTEST"
    strategy_type: str = "PARABOLIC_SAR"


class AppConfig(BaseSettings):
    """Application configuration using Pydantic Settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    default: DefaultConfig = Field(default_factory=DefaultConfig)  # type: ignore[assignment]
    exchange: ExchangeConfig = Field(default_factory=ExchangeConfig)  # type: ignore[assignment]
    logging: LoggingConfig = Field(default_factory=LoggingConfig)  # type: ignore[assignment]
    trading: TradingConfig = Field(default_factory=TradingConfig)  # type: ignore[assignment]

    def get_value(self, section: str, option: str, fallback: Any = None) -> Any:
        """Get a configuration value with fallback (backward compatibility)."""
        section_lower = section.lower()
        if section_lower == "default":
            return getattr(self.default, option, fallback)
        elif section_lower == "exchange":
            return getattr(self.exchange, option, fallback)
        elif section_lower == "logging":
            return getattr(self.logging, option, fallback)
        elif section_lower == "trading":
            return getattr(self.trading, option, fallback)
        return fallback

    def get_int(self, section: str, option: str, fallback: int = None) -> int:
        """Get an integer configuration value (backward compatibility)."""
        value = self.get_value(section, option, fallback)
        if value is None:
            return fallback
        return int(value)

    def get_float(self, section: str, option: str, fallback: float = None) -> float:
        """Get a float configuration value (backward compatibility)."""
        value = self.get_value(section, option, fallback)
        if value is None:
            return fallback
        return float(value)

    def get_boolean(self, section: str, option: str, fallback: bool = None) -> bool:
        """Get a boolean configuration value (backward compatibility)."""
        value = self.get_value(section, option, fallback)
        if value is None:
            return fallback
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    def has_section(self, section: str) -> bool:
        """Check if a section exists (backward compatibility)."""
        section_lower = section.lower()
        return section_lower in ("default", "exchange", "logging", "trading")

    def has_option(self, section: str, option: str) -> bool:
        """Check if an option exists in a section (backward compatibility)."""
        section_lower = section.lower()
        if section_lower == "default":
            return hasattr(self.default, option)
        elif section_lower == "exchange":
            return hasattr(self.exchange, option)
        elif section_lower == "logging":
            return hasattr(self.logging, option)
        elif section_lower == "trading":
            return hasattr(self.trading, option)
        return False

    def get_section(self, section: str) -> dict:
        """Get all options from a section (backward compatibility)."""
        section_lower = section.lower()
        section_map = {
            "default": lambda: getattr(self, "default", None),
            "exchange": lambda: getattr(self, "exchange", None),
            "logging": lambda: getattr(self, "logging", None),
            "trading": lambda: getattr(self, "trading", None),
        }

        section_obj = section_map.get(section_lower)
        if section_obj is None:
            raise KeyError(f"Section '{section}' not found")

        obj = section_obj()
        if obj is None:
            raise KeyError(f"Section '{section}' not found")

        # Use model_dump if available (Pydantic model), otherwise convert to dict
        if hasattr(obj, "model_dump"):
            return obj.model_dump()  # type: ignore[attr-defined]
        return dict(obj) if hasattr(obj, "__dict__") else {}


# Global config instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _config  # pylint: disable=global-statement
    if _config is None:
        _config = AppConfig()
    return _config


def reload_config() -> AppConfig:
    """Reload the configuration from file."""
    global _config  # pylint: disable=global-statement
    _config = AppConfig()
    return _config


# For backward compatibility
class ConfigManager:
    """Backward compatibility wrapper for ConfigManager."""

    @classmethod
    def get_config(cls) -> AppConfig:
        """Get the configuration."""
        return get_config()

    @classmethod
    def reload_config(cls) -> AppConfig:
        """Reload the configuration."""
        return reload_config()

    @classmethod
    def get_value(cls, section: str, option: str, fallback: Any = None) -> Any:
        """Get a configuration value with fallback."""
        return get_config().get_value(section, option, fallback)

    @classmethod
    def get_int(cls, section: str, option: str, fallback: int = None) -> int:
        """Get an integer configuration value."""
        return get_config().get_int(section, option, fallback)

    @classmethod
    def get_float(cls, section: str, option: str, fallback: float = None) -> float:
        """Get a float configuration value."""
        return get_config().get_float(section, option, fallback)

    @classmethod
    def get_boolean(cls, section: str, option: str, fallback: bool = None) -> bool:
        """Get a boolean configuration value."""
        return get_config().get_boolean(section, option, fallback)

    @classmethod
    def has_section(cls, section: str) -> bool:
        """Check if a section exists."""
        return get_config().has_section(section)

    @classmethod
    def has_option(cls, section: str, option: str) -> bool:
        """Check if an option exists in a section."""
        return get_config().has_option(section, option)

    @classmethod
    def get_section(cls, section: str) -> dict:
        """Get all options from a section."""
        return get_config().get_section(section)

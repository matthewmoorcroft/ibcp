"""Configuration management for the IBCP library."""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import tomllib

from .exceptions import ConfigurationError


@dataclass
class IBConfig:
    """Configuration class for IBCP library."""

    # Connection settings
    base_url: str = "https://localhost:5000"
    ssl_verify: bool = False
    timeout: int = 30
    max_retries: int = 3
    
    # Rate limiting
    rate_limit: int = 100  # requests per minute
    rate_limit_window: int = 60  # seconds
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Caching
    cache_enabled: bool = True
    cache_ttl: int = 300  # seconds (5 minutes)
    cache_max_size: int = 1000
    
    # WebSocket settings (for future use)
    ws_url: Optional[str] = None
    ws_heartbeat: int = 30
    ws_reconnect_attempts: int = 5
    
    # Development settings
    debug: bool = False
    
    # Additional settings
    extra_settings: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate_config()
        self._setup_logging()

    def _validate_config(self) -> None:
        """Validate configuration values."""
        if self.timeout <= 0:
            raise ConfigurationError("timeout must be positive")
        
        if self.max_retries < 0:
            raise ConfigurationError("max_retries must be non-negative")
        
        if self.rate_limit <= 0:
            raise ConfigurationError("rate_limit must be positive")
        
        if not self.base_url:
            raise ConfigurationError("base_url cannot be empty")
        
        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_levels:
            raise ConfigurationError(f"log_level must be one of {valid_levels}")

    def _setup_logging(self) -> None:
        """Set up logging configuration."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format=self.log_format,
        )

    @classmethod
    def from_file(cls, path: str) -> "IBConfig":
        """Load configuration from a TOML file.
        
        Args:
            path: Path to the configuration file
            
        Returns:
            IBConfig instance with loaded settings
            
        Raises:
            ConfigurationError: If file cannot be read or parsed
        """
        config_path = Path(path)
        
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {path}")
        
        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
            
            # Extract IBCP-specific configuration
            ibcp_config = data.get("ibcp", {})
            
            return cls(**ibcp_config)
        
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from {path}: {e}")

    @classmethod
    def from_env(cls, prefix: str = "IBCP_") -> "IBConfig":
        """Load configuration from environment variables.
        
        Args:
            prefix: Prefix for environment variables (default: "IBCP_")
            
        Returns:
            IBConfig instance with environment settings
        """
        env_config = {}
        
        # Map environment variables to config fields
        env_mappings = {
            f"{prefix}BASE_URL": "base_url",
            f"{prefix}SSL_VERIFY": "ssl_verify",
            f"{prefix}TIMEOUT": "timeout",
            f"{prefix}MAX_RETRIES": "max_retries",
            f"{prefix}RATE_LIMIT": "rate_limit",
            f"{prefix}LOG_LEVEL": "log_level",
            f"{prefix}DEBUG": "debug",
        }
        
        for env_var, config_key in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Type conversion
                if config_key in ["ssl_verify", "debug"]:
                    env_config[config_key] = value.lower() in ("true", "1", "yes", "on")
                elif config_key in ["timeout", "max_retries", "rate_limit"]:
                    try:
                        env_config[config_key] = int(value)
                    except ValueError:
                        raise ConfigurationError(f"Invalid integer value for {env_var}: {value}")
                else:
                    env_config[config_key] = value
        
        return cls(**env_config)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "IBConfig":
        """Create configuration from a dictionary.
        
        Args:
            config_dict: Dictionary with configuration values
            
        Returns:
            IBConfig instance
        """
        return cls(**config_dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of the configuration
        """
        return {
            "base_url": self.base_url,
            "ssl_verify": self.ssl_verify,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "rate_limit": self.rate_limit,
            "rate_limit_window": self.rate_limit_window,
            "log_level": self.log_level,
            "log_format": self.log_format,
            "cache_enabled": self.cache_enabled,
            "cache_ttl": self.cache_ttl,
            "cache_max_size": self.cache_max_size,
            "ws_url": self.ws_url,
            "ws_heartbeat": self.ws_heartbeat,
            "ws_reconnect_attempts": self.ws_reconnect_attempts,
            "debug": self.debug,
            "extra_settings": self.extra_settings,
        }

    def update(self, **kwargs: Any) -> None:
        """Update configuration values.
        
        Args:
            **kwargs: Configuration values to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.extra_settings[key] = value
        
        self._validate_config()
        self._setup_logging()

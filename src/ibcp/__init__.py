"""IBCP - Interactive Brokers Client Portal Python Wrapper.

A modern, type-safe Python wrapper for the Interactive Brokers Client Portal Web API.
"""

from .config import IBConfig
from .exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    ConnectionError,
    IBCPError,
    MarketDataError,
    OrderError,
    RateLimitError,
    ValidationError,
)
from .ibcp import REST


__version__ = "0.2.0-alpha"
__all__ = [
    # Main classes
    "REST",
    "IBConfig",
    # Exceptions
    "IBCPError",
    "APIError",
    "AuthenticationError",
    "ValidationError",
    "OrderError",
    "MarketDataError",
    "RateLimitError",
    "ConnectionError",
    "ConfigurationError",
]

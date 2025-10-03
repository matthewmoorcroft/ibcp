"""Custom exceptions for the IBCP library."""

from typing import Any, Optional


class IBCPError(Exception):
    """Base exception for all IBCP library errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class APIError(IBCPError):
    """Exception raised for API request errors."""

    def __init__(
        self,
        message: str,
        status_code: int,
        response: dict[str, Any],
        endpoint: Optional[str] = None,
    ) -> None:
        super().__init__(message, {"status_code": status_code, "response": response})
        self.status_code = status_code
        self.response = response
        self.endpoint = endpoint

    def __str__(self) -> str:
        endpoint_info = f" (endpoint: {self.endpoint})" if self.endpoint else ""
        return f"API Error {self.status_code}: {self.message}{endpoint_info}"


class AuthenticationError(IBCPError):
    """Exception raised for authentication-related errors."""

    pass


class ValidationError(IBCPError):
    """Exception raised for input validation errors."""

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        super().__init__(message, {"field": field})
        self.field = field


class OrderError(IBCPError):
    """Exception raised for order-related errors."""

    def __init__(
        self,
        message: str,
        order_data: Optional[dict[str, Any]] = None,
        order_id: Optional[str] = None,
    ) -> None:
        super().__init__(message, {"order_data": order_data, "order_id": order_id})
        self.order_data = order_data
        self.order_id = order_id


class MarketDataError(IBCPError):
    """Exception raised for market data related errors."""

    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        contract_id: Optional[int] = None,
    ) -> None:
        super().__init__(message, {"symbol": symbol, "contract_id": contract_id})
        self.symbol = symbol
        self.contract_id = contract_id


class RateLimitError(APIError):
    """Exception raised when API rate limits are exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        endpoint: Optional[str] = None,
    ) -> None:
        super().__init__(message, 429, {"retry_after": retry_after}, endpoint)
        self.retry_after = retry_after


class ConnectionError(IBCPError):
    """Exception raised for connection-related errors."""

    pass


class ConfigurationError(IBCPError):
    """Exception raised for configuration-related errors."""

    pass

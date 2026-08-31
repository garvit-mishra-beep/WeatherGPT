"""Meteorological Data Adapter Error Hierarchy."""

from typing import Optional


class AdapterError(Exception):
    """Base exception for all meteorological adapter errors."""

    def __init__(
        self,
        message: str,
        code: str = "ADAPTER_ERROR",
        provider: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.provider = provider
        self.details = details or {}


class ProviderUnavailableError(AdapterError):
    """Raised when an external weather provider cannot be reached."""

    def __init__(self, message: str, provider: Optional[str] = None, details: Optional[dict] = None) -> None:
        super().__init__(message, code="PROVIDER_UNAVAILABLE", provider=provider, details=details)


class ProviderTimeoutError(AdapterError):
    """Raised when an external weather provider request times out."""

    def __init__(self, message: str, provider: Optional[str] = None, details: Optional[dict] = None) -> None:
        super().__init__(message, code="PROVIDER_TIMEOUT", provider=provider, details=details)


class ProviderResponseError(AdapterError):
    """Raised when an external weather provider returns a non-2xx HTTP status or unexpected payload."""

    def __init__(self, message: str, provider: Optional[str] = None, status_code: Optional[int] = None, details: Optional[dict] = None) -> None:
        super().__init__(message, code="PROVIDER_RESPONSE_ERROR", provider=provider, details=details)
        self.status_code = status_code


class ProviderRateLimitError(ProviderResponseError):
    """Raised when an external weather provider throttles requests (HTTP 429)."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        retry_after_seconds: Optional[float] = None,
        details: Optional[dict] = None,
    ) -> None:
        super().__init__(message, provider=provider, status_code=429, details=details)
        self.code = "PROVIDER_RATE_LIMIT"
        self.retry_after_seconds = retry_after_seconds


class ProviderCircuitOpenError(ProviderUnavailableError):
    """Raised when provider circuit breaker is OPEN and fast-fails requests."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        retry_after_seconds: Optional[float] = None,
        details: Optional[dict] = None,
    ) -> None:
        super().__init__(message, provider=provider, details=details)
        self.code = "PROVIDER_CIRCUIT_OPEN"
        self.retry_after_seconds = retry_after_seconds


class ProviderValidationError(AdapterError):
    """Raised when provider payload fails structural or physical validation."""

    def __init__(self, message: str, provider: Optional[str] = None, details: Optional[dict] = None) -> None:
        super().__init__(message, code="PROVIDER_VALIDATION_ERROR", provider=provider, details=details)


class UnsupportedDataFormatError(AdapterError):
    """Raised when payload format is not recognized or supported."""

    def __init__(self, message: str, provider: Optional[str] = None, details: Optional[dict] = None) -> None:
        super().__init__(message, code="UNSUPPORTED_DATA_FORMAT", provider=provider, details=details)


class CAPParseError(AdapterError):
    """Raised when OASIS CAP XML alert feed fails parsing or lacks required fields."""

    def __init__(self, message: str, provider: str = "IMD", details: Optional[dict] = None) -> None:
        super().__init__(message, code="CAP_PARSE_ERROR", provider=provider, details=details)


class GRIBParseError(AdapterError):
    """Raised when GRIB2 numerical weather file is corrupt, truncated, or unparseable."""

    def __init__(self, message: str, provider: str = "GFS", details: Optional[dict] = None) -> None:
        super().__init__(message, code="GRIB_PARSE_ERROR", provider=provider, details=details)

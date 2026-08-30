"""Backend domain exception taxonomy (exception type definitions only).

Separated from :mod:`app.core.exceptions` (which contains the FastAPI exception
handlers) to avoid an import cycle: ``app.core.request_id`` raises
:class:`InvalidRequestIdError` and must not transitively import the handler
module.
"""

from typing import Any, Dict, Optional


class BackendError(Exception):
    """Base class for all recoverable WeatherGPT backend application errors."""

    status_code: int = 500
    title: str = "Internal Server Error"
    error_code: str = "BACKEND_ERROR"

    def __init__(
        self,
        detail: str,
        *,
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.error_code = error_code or self.error_code
        self.status_code = status_code or self.status_code
        self.extra = extra or {}


class NotFoundError(BackendError):
    status_code = 404
    title = "Resource Not Found"
    error_code = "NOT_FOUND"


class ConflictError(BackendError):
    status_code = 409
    title = "Conflict"
    error_code = "CONFLICT"


class ServiceUnavailableError(BackendError):
    status_code = 503
    title = "Service Unavailable"
    error_code = "SERVICE_UNAVAILABLE"


class InvalidRequestIdError(BackendError):
    status_code = 400
    title = "Invalid Request ID"
    error_code = "INVALID_REQUEST_ID"

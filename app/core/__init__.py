"""WeatherGPT backend core infrastructure package.

Houses cross-cutting plumbing: configuration-driven structured logging, request
correlation IDs, HTTP middleware, exception handling, application lifecycle, and
the pluggable readiness mechanism. Domain logic intentionally does **not** live
here.
"""

from app.core.errors import (
    BackendError,
    ConflictError,
    InvalidRequestIdError,
    NotFoundError,
    ServiceUnavailableError,
)

__all__ = [
    "BackendError",
    "NotFoundError",
    "ConflictError",
    "ServiceUnavailableError",
    "InvalidRequestIdError",
]

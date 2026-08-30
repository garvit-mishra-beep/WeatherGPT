"""Request correlation ID handling for the WeatherGPT backend.

Provides a contextvar-backed request ID that is:
  * accepted from a trusted inbound ``X-Request-ID`` header when valid,
  * otherwise generated locally,
  * available to application code via :func:`get_request_id`,
  * attached to structured log records,
  * echoed back on the outbound response.
"""

import re
import uuid
from contextvars import ContextVar

from app.core.errors import InvalidRequestIdError

_REQUEST_ID_HEADER = "X-Request-ID"

# Whitelist of characters that are safe to trust from clients. Anything else is
# rejected so we never propagate a value that could smuggle log-injection or
# header-injection payloads.
_VALID_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

_request_id_var: ContextVar[str] = ContextVar("weathergpt_request_id", default="")


def is_valid_request_id(value: str) -> bool:
    """Return whether ``value`` is an acceptable inbound request ID."""
    return bool(value) and _VALID_REQUEST_ID_RE.fullmatch(value) is not None


def generate_request_id() -> str:
    """Generate a fresh, collision-resistant request ID."""
    return uuid.uuid4().hex


def normalize_request_id(raw: str | None) -> str:
    """Coerce a client-supplied header into a validated request ID.

    Args:
        raw: Raw header value, or ``None``/empty for a new ID.

    Returns:
        A validated request ID string.

    Raises:
        InvalidRequestIdError: If ``raw`` is present but fails strict validation.
    """
    if not raw or not raw.strip():
        return generate_request_id()
    candidate = raw.strip()
    if not is_valid_request_id(candidate):
        raise InvalidRequestIdError(
            f"Request ID '{raw[:64]}' contains disallowed characters."
        )
    return candidate


def set_request_id(request_id: str) -> None:
    """Bind a request ID to the current async context."""
    _request_id_var.set(request_id)


def get_request_id() -> str:
    """Return the active request ID (empty string outside a request scope)."""
    return _request_id_var.get()

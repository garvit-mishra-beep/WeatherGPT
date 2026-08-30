"""Configurable structured logging for the WeatherGPT backend.

B1 provides a JSON-friendly structured log formatter that captures the standard
fields (timestamp, level, request ID, logger, message) plus any structured extra
fields. It is container-friendly: output is written to stdout so that log
collectors (e.g. Docker, k8s, cloud logging) can ingest it without mount hacks.

Security: the formatter never logs the raw ``Authorization`` header, API keys, or
credentials. Sensitive header names are redacted at the middleware layer and the
formatter drops ``exc_info`` text unless explicitly requested by the configured
log level (ERROR and above retain tracebacks for development-only diagnosis).
"""

import json
import logging
import sys
import time
from typing import Any, Dict

from app.config import Settings

_SENSITIVE_EXTRA_KEYS = {"secret", "api_key", "password", "token", "authorization"}


class StructuredJsonFormatter(logging.Formatter):
    """Format log records as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        entry: Dict[str, Any] = {
            "timestamp": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Fold structured extras from logging (e.g. request_id=..., method=...)
        for key in ("request_id", "method", "path", "status", "duration_ms", "client"):
            value = getattr(record, key, None)
            if value is not None:
                entry[key] = value

        # Do not propagate sensitive extra keys even if a caller sets them.
        for key in list(record.__dict__.keys()):
            lowered = key.lower()
            if any(s in lowered for s in _SENSITIVE_EXTRA_KEYS):
                entry[key] = "[REDACTED]"

        if record.exc_info and record.levelno >= logging.ERROR:
            entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(entry, ensure_ascii=False, default=str)


def configure_logging(settings: Settings) -> None:
    """Configure the root logger with structured formatting for the given settings."""
    root = logging.getLogger()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Idempotent: avoid stacking duplicate handlers across app re-initialization.
    root.handlers.clear()
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)

    # Keep third-party loggers (uvicorn, httpx) at a sane verbosity.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

"""HTTP middleware for the WeatherGPT backend.

B1 includes only lightweight, genuinely useful middleware:

  * ``RequestIDMiddleware``   — propagate/validate/generate ``X-Request-ID``.
  * ``RequestContextLoggingMiddleware`` — timing + structured access logging.

Domain logic must never live in middleware; these are pure plumbing.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.errors import InvalidRequestIdError
from app.core.metrics import api_metrics, normalize_route
from app.core.request_id import (
    _REQUEST_ID_HEADER,
    get_request_id,
    normalize_request_id,
    set_request_id,
)

logger = logging.getLogger(__name__)

# Headers that must never be emitted into logs/access entries.
_SENSITIVE_HEADERS = {"authorization", "cookie", "x-api-key", "proxy-authorization"}


class APIMetricsMiddleware(BaseHTTPMiddleware):
    """Collect HTTP/API observability metrics using low-cardinality labels and monotonic clocks."""

    async def dispatch(self, request: Request, call_next):
        method = request.method
        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            duration_seconds = time.perf_counter() - start_time
            route = normalize_route(request)
            api_metrics.record_request(method, route)
            api_metrics.record_response(method, route, response.status_code, duration_seconds)
            return response
        except Exception:
            duration_seconds = time.perf_counter() - start_time
            route = normalize_route(request)
            api_metrics.record_request(method, route)
            api_metrics.record_response(method, route, 500, duration_seconds)
            raise


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Ensure every request carries a validated, propagated request ID."""

    async def dispatch(self, request: Request, call_next):
        raw_id = request.headers.get(_REQUEST_ID_HEADER)
        try:
            request_id = normalize_request_id(raw_id)
        except InvalidRequestIdError as exc:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=400,
                content={
                    "type": "https://weathergpt.in/errors/INVALID_REQUEST_ID",
                    "title": "Invalid Request ID",
                    "status": 400,
                    "detail": exc.detail,
                    "instance": str(request.url.path),
                    "error_code": "INVALID_REQUEST_ID",
                },
                media_type="application/problem+json",
            )

        set_request_id(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            # Provide the timing to downstream logging middleware/log records.
            logger.debug(
                "Request processed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(elapsed_ms, 3),
                },
            )

        response.headers[_REQUEST_ID_HEADER] = request_id
        return response


class RequestContextLoggingMiddleware(BaseHTTPMiddleware):
    """Log a single structured request lifecycle line per HTTP request.

    Runs inside the request-ID scope (registered after RequestIDMiddleware so the
    request ID is already bound). Never logs sensitive headers or bodies.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = get_request_id()
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000.0
            logger.error(
                "request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": 500,
                    "duration_ms": round(duration_ms, 3),
                },
            )
            raise
        duration_ms = (time.perf_counter() - start) * 1000.0
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 3),
            },
        )
        return response


def sensitive_headers(headers: dict) -> dict:
    """Return a scrubbed copy of ``headers`` for any logging/allowed-list use."""
    return {k: ("[REDACTED]" if k.lower() in _SENSITIVE_HEADERS else v) for k, v in headers.items()}

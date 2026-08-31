"""Sliding-window In-Memory API Rate Limiter and Middleware.

Provides application-level rate limiting with configurable per-endpoint thresholds,
monotonic sliding window tracking, Retry-After calculation, and RFC 7807 problem responses.

NOTE: This is a process-local in-memory limiter. In multi-worker native Linux deployments
(FastAPI with 4 Uvicorn workers), edge-level coarse rate limiting is provided by Nginx
(e.g., limit_req_zone), while this middleware provides granular endpoint-specific protection.
"""

from collections import defaultdict, deque
import logging
import threading
import time
from typing import Dict, List, Optional, Tuple
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import Settings, settings as default_settings
from app.core.request_id import get_request_id

logger = logging.getLogger(__name__)


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding window rate limiter."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or default_settings
        self._lock = threading.Lock()
        # (client_ip, endpoint_bucket) -> deque of monotonic timestamps
        self._history: Dict[Tuple[str, str], deque] = defaultdict(deque)

    def _get_limit_and_bucket(self, path: str) -> Tuple[Optional[int], str]:
        """Categorize path into rate-limit bucket and return max allowable requests."""
        # Health and readiness probes are unthrottled
        if path.startswith("/api/v1/health") or path.startswith("/api/v1/ready"):
            return None, "health"
        if path.startswith("/api/v1/chat"):
            return self.settings.rate_limit_chat_requests, "chat"
        if path.startswith("/api/v1/weather"):
            return self.settings.rate_limit_weather_requests, "weather"
        if path.startswith("/api/v1/nwp"):
            return self.settings.rate_limit_nwp_requests, "nwp"
        if path.startswith("/api/v1/gis"):
            return self.settings.rate_limit_gis_requests, "gis"
        return self.settings.rate_limit_default_requests, "default"

    def check_rate_limit(self, client_ip: str, path: str) -> Tuple[bool, int]:
        """Check if request is allowed under rate limits.

        Returns:
            Tuple[bool, int]: (allowed, retry_after_seconds)
        """
        if not self.settings.rate_limit_enabled:
            return True, 0

        limit, bucket = self._get_limit_and_bucket(path)
        if limit is None:
            return True, 0

        window = self.settings.rate_limit_window_seconds
        now = time.monotonic()
        cutoff = now - window

        with self._lock:
            history = self._history[(client_ip, bucket)]

            # Evict timestamps outside sliding window
            while history and history[0] < cutoff:
                history.popleft()

            if len(history) >= limit:
                # Calculate remaining seconds until oldest request expires
                oldest = history[0]
                retry_after = max(1, int(oldest + window - now) + 1)
                return False, retry_after

            # Record current request
            history.append(now)
            return True, 0

    def reset(self) -> None:
        """Clear all in-memory rate limit histories."""
        with self._lock:
            self._history.clear()


default_rate_limiter = SlidingWindowRateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract client IP address safely from headers or connection scope."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # First IP in comma-separated chain is the client IP
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Starlette middleware intercepting requests to enforce rate limits."""

    def __init__(self, app, limiter: Optional[SlidingWindowRateLimiter] = None) -> None:
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next):
        limiter = self.limiter
        if limiter is None:
            limiter = getattr(request.app.state, "rate_limiter", None) or default_rate_limiter

        client_ip = get_client_ip(request)
        path = request.url.path

        allowed, retry_after = limiter.check_rate_limit(client_ip, path)
        if not allowed:
            request_id = get_request_id() or "unknown"
            logger.warning(
                "Rate limit exceeded for path '%s' (Retry-After: %ds)",
                path,
                retry_after,
            )
            response_content = {
                "type": "https://weathergpt.in/errors/RATE_LIMIT_EXCEEDED",
                "title": "Too Many Requests",
                "status": 429,
                "detail": f"Rate limit exceeded. Please retry in {retry_after} seconds.",
                "instance": str(path),
                "error_code": "RATE_LIMIT_EXCEEDED",
                "request_id": request_id,
                "retryable": True,
                "retry_after_seconds": retry_after,
            }
            return JSONResponse(
                status_code=429,
                content=response_content,
                headers={"Retry-After": str(retry_after)},
                media_type="application/problem+json",
            )

        return await call_next(request)

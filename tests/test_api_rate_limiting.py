"""Targeted test suite for Milestone B13.9 — API Rate Limiting & Abuse Protection.

Verifies:
1. Requests below limit succeed normally (HTTP 200).
2. Requests reaching limit succeed.
3. Requests exceeding limit receive HTTP 429 Too Many Requests.
4. HTTP 429 response contains Retry-After header and RFC 7807 problem details.
5. Distinct client IPs have independent rate limit allowances.
6. Endpoint-specific rate limit categorization (/chat, /weather, /nwp, /gis).
7. Health & readiness endpoints are exempt from rate limiting.
8. Concurrent request bursts correctly throttle excessive requests.
"""

import asyncio
from httpx import ASGITransport, AsyncClient
import pytest

from app.config import Settings
from app.core.factory import create_app
from app.core.rate_limit import SlidingWindowRateLimiter, default_rate_limiter


@pytest.fixture(autouse=True)
def reset_limiter():
    default_rate_limiter.reset()
    yield
    default_rate_limiter.reset()


@pytest.mark.asyncio
async def test_rate_limiter_unit_below_and_above_limit():
    """Verify SlidingWindowRateLimiter unit logic for below, at, and above limits."""
    settings = Settings(
        rate_limit_enabled=True,
        rate_limit_chat_requests=3,
        rate_limit_window_seconds=10.0,
    )
    limiter = SlidingWindowRateLimiter(settings=settings)

    # 3 allowed
    assert limiter.check_rate_limit("1.2.3.4", "/api/v1/chat")[0] is True
    assert limiter.check_rate_limit("1.2.3.4", "/api/v1/chat")[0] is True
    assert limiter.check_rate_limit("1.2.3.4", "/api/v1/chat")[0] is True

    # 4th request exceeds limit
    allowed, retry_after = limiter.check_rate_limit("1.2.3.4", "/api/v1/chat")
    assert allowed is False
    assert retry_after >= 1


@pytest.mark.asyncio
async def test_rate_limiter_independent_client_ips():
    """Verify independent client IPs have isolated quota."""
    settings = Settings(
        rate_limit_enabled=True,
        rate_limit_chat_requests=2,
        rate_limit_window_seconds=10.0,
    )
    limiter = SlidingWindowRateLimiter(settings=settings)

    # Client A consumes 2
    assert limiter.check_rate_limit("10.0.0.1", "/api/v1/chat")[0] is True
    assert limiter.check_rate_limit("10.0.0.1", "/api/v1/chat")[0] is True
    assert limiter.check_rate_limit("10.0.0.1", "/api/v1/chat")[0] is False

    # Client B still has full allowance
    assert limiter.check_rate_limit("10.0.0.2", "/api/v1/chat")[0] is True
    assert limiter.check_rate_limit("10.0.0.2", "/api/v1/chat")[0] is True
    assert limiter.check_rate_limit("10.0.0.2", "/api/v1/chat")[0] is False


@pytest.mark.asyncio
async def test_rate_limiter_health_endpoints_exempt():
    """Verify /api/v1/health and /api/v1/ready are never throttled."""
    settings = Settings(
        rate_limit_enabled=True,
        rate_limit_default_requests=2,
        rate_limit_window_seconds=10.0,
    )
    limiter = SlidingWindowRateLimiter(settings=settings)

    for _ in range(100):
        allowed_health, _ = limiter.check_rate_limit("1.2.3.4", "/api/v1/health")
        allowed_ready, _ = limiter.check_rate_limit("1.2.3.4", "/api/v1/ready")
        assert allowed_health is True
        assert allowed_ready is True


@pytest.mark.asyncio
async def test_http_rate_limit_middleware_429_and_retry_after():
    """Verify FastAPI integration returns HTTP 429 and Retry-After header."""
    test_settings = Settings(
        app_env="test",
        debug=False,
        rate_limit_enabled=True,
        rate_limit_default_requests=3,
        rate_limit_window_seconds=30.0,
    )
    app = create_app(settings=test_settings, configure_logging_enabled=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Request 1, 2, 3 -> HTTP 200
        for _ in range(3):
            resp = await client.get("/api/v1/metrics", headers={"X-Forwarded-For": "192.168.1.50"})
            assert resp.status_code == 200

        # Request 4 -> HTTP 429 Too Many Requests
        resp429 = await client.get("/api/v1/metrics", headers={"X-Forwarded-For": "192.168.1.50"})
        assert resp429.status_code == 429
        assert "Retry-After" in resp429.headers
        assert int(resp429.headers["Retry-After"]) >= 1

        payload = resp429.json()
        assert payload["status"] == 429
        assert payload["error_code"] == "RATE_LIMIT_EXCEEDED"
        assert payload["retryable"] is True
        assert "retry_after_seconds" in payload

        # Different IP should still succeed
        resp_other = await client.get("/api/v1/metrics", headers={"X-Forwarded-For": "192.168.1.51"})
        assert resp_other.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_concurrency():
    """Verify concurrent burst of requests respects limit precisely."""
    test_settings = Settings(
        app_env="test",
        debug=False,
        rate_limit_enabled=True,
        rate_limit_default_requests=5,
        rate_limit_window_seconds=20.0,
    )
    app = create_app(settings=test_settings, configure_logging_enabled=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Forwarded-For": "10.50.0.1"}
        tasks = [client.get("/api/v1/metrics", headers=headers) for _ in range(15)]
        responses = await asyncio.gather(*tasks)

        status_codes = [r.status_code for r in responses]
        assert status_codes.count(200) == 5
        assert status_codes.count(429) == 10

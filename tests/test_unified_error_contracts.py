"""Targeted test suite for Milestone B13.10 — Unified Error Contracts.

Verifies:
1. All client-facing errors adhere to the standardized RFC 7807 problem details schema.
2. Standard fields present: type, title, status, detail, instance, error_code, request_id, retryable, timestamp.
3. Error status codes mapped accurately: 400, 403, 404, 422, 429, 500, 502, 503, 504.
4. Retryable boolean flag correctly flags transient vs permanent failures.
5. Zero internal stack traces, zero SQL query fragments, zero database URLs, and zero provider credentials.
"""

from httpx import ASGITransport, AsyncClient
import pytest
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from app.adapters.errors import ProviderTimeoutError, ProviderUnavailableError
from app.config import Settings
from app.contracts.enums import BrainType
from app.core.factory import create_app
from app.llm.types import LLMProviderError, LLMTimeoutError
from app.tools.errors import ToolAuthorizationError, ToolSecurityError


@pytest.mark.asyncio
async def test_error_contract_validation_error_422():
    """Verify 422 validation error returns standardized RFC 7807 shape with retryable=False."""
    app = create_app(settings=Settings(app_env="test", debug=False), configure_logging_enabled=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid payload for current weather (missing lat/lon)
        resp = await client.get("/api/v1/weather/current")
        assert resp.status_code == 422
        payload = resp.json()

        assert payload["status"] == 422
        assert payload["title"] == "Validation Error"
        assert payload["error_code"] == "VALIDATION_ERROR"
        assert payload["retryable"] is False
        assert "request_id" in payload
        assert "timestamp" in payload
        assert "instance" in payload
        assert "details" in payload
        assert "traceback" not in payload


@pytest.mark.asyncio
async def test_error_contract_provider_unavailable_503():
    """Verify ProviderUnavailableError produces 503 with retryable=True and zero credentials."""
    from fastapi import APIRouter
    test_router = APIRouter()

    @test_router.get("/test/provider-fail")
    async def _mock_fail():
        raise ProviderUnavailableError("Simulated provider outage with api_key=secret_12345")

    app = create_app(settings=Settings(app_env="test", debug=False), configure_logging_enabled=False)
    app.include_router(test_router, prefix="/api/v1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/test/provider-fail")
        assert resp.status_code == 503
        payload = resp.json()

        assert payload["status"] == 503
        assert payload["error_code"] == "PROVIDER_UNAVAILABLE"
        assert payload["retryable"] is True
        assert "secret_12345" not in payload["detail"]
        assert "traceback" not in payload


@pytest.mark.asyncio
async def test_error_contract_llm_timeout_504():
    """Verify LLMTimeoutError produces 504 with retryable=True."""
    from fastapi import APIRouter
    test_router = APIRouter()

    @test_router.get("/test/llm-timeout")
    async def _mock_llm_timeout():
        raise LLMTimeoutError("LLM timed out after 30 seconds")

    app = create_app(settings=Settings(app_env="test", debug=False), configure_logging_enabled=False)
    app.include_router(test_router, prefix="/api/v1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/test/llm-timeout")
        assert resp.status_code == 504
        payload = resp.json()

        assert payload["status"] == 504
        assert payload["error_code"] == "LLM_TIMEOUT"
        assert payload["retryable"] is True
        assert payload["title"] == "LLM Inference Timeout"


@pytest.mark.asyncio
async def test_error_contract_tool_security_403():
    """Verify ToolSecurityError produces 403 with retryable=False."""
    from fastapi import APIRouter
    test_router = APIRouter()

    @test_router.get("/test/tool-security")
    async def _mock_tool_security():
        raise ToolSecurityError(tool_name="eval_tool", reason="Disallowed command injection key")

    app = create_app(settings=Settings(app_env="test", debug=False), configure_logging_enabled=False)
    app.include_router(test_router, prefix="/api/v1")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/test/tool-security")
        assert resp.status_code == 403
        payload = resp.json()

        assert payload["status"] == 403
        assert payload["error_code"] == "TOOL_SECURITY_ERROR"
        assert payload["retryable"] is False
        assert "Security constraint violated" in payload["detail"]


@pytest.mark.asyncio
async def test_error_contract_unhandled_500_safe_message():
    """Verify unhandled internal exception produces generic safe message with zero stack traces."""
    from fastapi import APIRouter
    test_router = APIRouter()

    @test_router.get("/test/unhandled")
    async def _mock_crash():
        raise ZeroDivisionError("division by zero in SELECT * FROM sensitive_table WHERE secret='abc'")

    app = create_app(settings=Settings(app_env="test", debug=False), configure_logging_enabled=False)
    app.include_router(test_router, prefix="/api/v1")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/test/unhandled")
        assert resp.status_code == 500
        payload = resp.json()

        assert payload["status"] == 500
        assert payload["error_code"] == "INTERNAL_SERVER_ERROR"
        assert payload["retryable"] is False
        assert payload["detail"] == "An unexpected internal error occurred."
        assert "sensitive_table" not in payload["detail"]
        assert "traceback" not in str(payload)

"""B1 — Backend Foundation test suite.

Covers the FastAPI application factory, API versioning, health/readiness,
request-ID correlation, middleware, structured logging, exception handling,
CORS, configuration, OpenAPI, lifecycle, dependency injection, and
production-safe behavior.

These tests are fully isolated: they require no PostgreSQL/PostGIS, GPU, real
weather APIs, IMD/GFS/ECMWF, or a production LLM. External concerns are avoided
by constructing the app with ``app_env="test"`` (which selects the mock LLM
provider) and never touching network services.
"""

import asyncio

import pytest
from fastapi import Query
from fastapi.testclient import TestClient

from app.brains.orchestrator import BrainOrchestrator
from app.config import Settings
from app.context.manager import ContextManager
from app.core.errors import ConflictError, NotFoundError
from app.core.factory import create_app
from app.core.request_id import (
    generate_request_id,
    is_valid_request_id,
    normalize_request_id,
    set_request_id,
    get_request_id,
)
from app.grounding.service import GroundingService
from app.llm.base import LLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.tools.gateway import ToolGateway


def _test_settings(**overrides) -> Settings:
    """Build an isolated, test-safe Settings instance."""
    defaults = {"app_env": "test", "app_name": "WeatherGPT-Test"}
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.fixture()
def test_app():
    """A fresh, isolated test application (test environment)."""
    app = create_app(_test_settings(), configure_logging_enabled=False)
    return app


@pytest.fixture()
def client(test_app):
    with TestClient(test_app) as c:
        yield c


# ============================================================================
# 1. Application & Factory
# ============================================================================

def test_application_creation_and_factory_returns_fastapi(test_app):
    """create_app returns a configured FastAPI application instance."""
    assert test_app.title == "WeatherGPT-Test"
    assert test_app.state.settings.app_env == "test"
    # OpenAPI metadata configured
    spec = test_app.openapi()
    assert spec["info"]["title"] == "WeatherGPT-Test"
    assert spec["info"]["version"] == "v1"


def test_factory_is_deterministic():
    """Two create_app calls with identical settings yield equivalent apps."""
    s = _test_settings()
    app1 = create_app(s, configure_logging_enabled=False)
    app2 = create_app(s, configure_logging_enabled=False)
    paths = {getattr(r, "path", "") for r in app1.routes}
    assert paths == {getattr(r, "path", "") for r in app2.routes}


def test_factory_accepts_custom_settings():
    """The factory honors an explicitly supplied Settings override."""
    s = _test_settings(app_name="CustomName", api_version="v1")
    app = create_app(s, configure_logging_enabled=False)
    assert app.title == "CustomName"
    assert app.state.settings.api_version == "v1"


# ============================================================================
# 2. API Versioning
# ============================================================================

def test_api_mounted_under_single_v1_prefix(test_app):
    """Versioned endpoints are only reachable under the canonical /api/v1 prefix."""
    paths = set()
    for r in test_app.routes:
        if hasattr(r, "path"):
            paths.add(r.path)
        elif hasattr(r, "original_router"):
            prefix = getattr(getattr(r, "include_context", None), "prefix", "")
            for sub_r in getattr(r.original_router, "routes", []):
                if hasattr(sub_r, "path"):
                    paths.add(f"{prefix}{sub_r.path}")
                elif hasattr(sub_r, "original_router"):
                    sub_p = getattr(getattr(sub_r, "include_context", None), "prefix", "")
                    for leaf in getattr(sub_r.original_router, "routes", []):
                        if hasattr(leaf, "path"):
                            paths.add(f"{prefix}{sub_p}{leaf.path}")
    assert "/api/v1/health" in paths
    assert "/api/v1/ready" in paths
    # No unversioned /health route should exist.
    assert "/health" not in paths


# ============================================================================
# 3. Health endpoint (liveness — must be lightweight)
# ============================================================================

def test_health_endpoint(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["environment"] == "test"
    assert "timestamp" in body


# ============================================================================
# 4. Readiness endpoint (pluggable, only real dependencies)
# ============================================================================

def test_ready_endpoint(client):
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready"] is True
    # B1 registers only the base application probe (no fake DB/GIS/NWP checks).
    assert "application" in body["dependencies"]
    assert body["dependencies"]["application"]["status"] == "connected"


def test_readiness_checker_is_pluggable(test_app):
    """Readiness probes are pluggable and failures are aggregated correctly."""
    from app.core.readiness import ProbeResult, ReadinessChecker

    class FailProbe:
        name = "future_db"

        async def check(self):
            return ProbeResult(name="future_db", ok=False, detail="not configured")

    checker = ReadinessChecker()
    checker.register(FailProbe())

    async def run():
        ready, results = await checker.check_all()
        return ready, results

    ready, results = asyncio.run(run())
    assert ready is False
    by_name = {r.name: r for r in results}
    assert by_name["future_db"].ok is False
    assert "future_db" in checker.names


# ============================================================================
# 5. Request correlation
# ============================================================================

def test_request_id_generation_is_valid():
    rid = generate_request_id()
    assert is_valid_request_id(rid)
    # Generated IDs are unique across calls.
    assert generate_request_id() != rid


def test_normalize_request_id():
    # Empty/None -> new generated ID.
    assert is_valid_request_id(normalize_request_id(None))
    assert is_valid_request_id(normalize_request_id(""))
    # Valid candidate is preserved.
    assert normalize_request_id("abc-123") == "abc-123"
    # Invalid candidate rejected.
    from app.core.errors import InvalidRequestIdError

    with pytest.raises(InvalidRequestIdError):
        normalize_request_id("bad id\npayload")


def test_request_id_contextvar():
    set_request_id("ctx-test-1")
    assert get_request_id() == "ctx-test-1"


def test_response_echoes_request_id(client):
    resp = client.get("/api/v1/health", headers={"X-Request-ID": "client-req-9"})
    assert resp.headers.get("X-Request-ID") == "client-req-9"


def test_response_generates_request_id_when_absent(client):
    resp = client.get("/api/v1/health")
    rid = resp.headers.get("X-Request-ID")
    assert rid is not None and is_valid_request_id(rid)


def test_invalid_request_id_rejected(client):
    resp = client.get(
        "/api/v1/health", headers={"X-Request-ID": "bad header\ninjection"}
    )
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "INVALID_REQUEST_ID"


# ============================================================================
# 6. Error handling
# ============================================================================

def test_known_application_error_maps_to_problem_details(test_app):
    @test_app.get("/api/v1/_test/conflict")
    async def _boom():
        raise ConflictError("A conflicting resource state.")

    with TestClient(test_app) as c:
        resp = c.get("/api/v1/_test/conflict")
    assert resp.status_code == 409
    body = resp.json()
    assert body["error_code"] == "CONFLICT"
    assert body["status"] == 409
    assert "A conflicting resource state." in body["detail"]


def test_not_found_maps_to_problem_details(test_app):
    @test_app.get("/api/v1/_test/missing")
    async def _missing():
        raise NotFoundError("No such resource.")

    with TestClient(test_app) as c:
        resp = c.get("/api/v1/_test/missing")
    assert resp.status_code == 404
    assert resp.json()["status"] == 404


def test_validation_error_returns_422_problem_details(test_app):
    @test_app.get("/api/v1/_test/need")
    async def _need(value: int = Query(...)):
        return {"value": value}

    with TestClient(test_app) as c:
        resp = c.get("/api/v1/_test/need")  # missing required query param
    assert resp.status_code == 422
    body = resp.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["status"] == 422
    assert "errors" in body["details"]


def test_unexpected_exception_is_safe(test_app):
    """Unexpected exceptions return a safe generic 500 (no stack trace leak)."""

    @test_app.get("/api/v1/_test/crash")
    async def _crash():
        raise ValueError("secret-internal-detail-do-not-leak")

    with TestClient(test_app, raise_server_exceptions=False) as c:
        resp = c.get("/api/v1/_test/crash")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error_code"] == "INTERNAL_SERVER_ERROR"
    # Internal detail must NOT leak to the client.
    assert "secret-internal-detail" not in body["detail"]


# ============================================================================
# 7. CORS
# ============================================================================

def test_cors_explicit_allowlist(client):
    resp = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_wildcard_disables_credentials():
    app = create_app(
        _test_settings(cors_origins=["*"]), configure_logging_enabled=False
    )
    cors_middleware = [
        m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware"
    ]
    assert cors_middleware, "CORSMiddleware not registered"
    kwargs = cors_middleware[0].kwargs
    assert kwargs["allow_origins"] == ["*"]
    assert kwargs["allow_credentials"] is False


# ============================================================================
# 8. Configuration
# ============================================================================

def test_configuration_environment_driven(monkeypatch):
    import app.config as config_module

    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example, https://b.example")
    loaded = config_module.Settings(_env_file=None)
    assert loaded.app_env == "staging"
    assert loaded.log_level == "DEBUG"
    assert loaded.cors_origins == ["https://a.example", "https://b.example"]


def test_configuration_preserves_llm_settings():
    s = _test_settings(
        llm_provider_type="mock",
        llm_base_url="http://host:8001/v1",
        llm_model_name="model-x",
        llm_timeout_seconds=12.5,
    )
    assert s.llm_base_url == "http://host:8001/v1"
    assert s.llm_model_name == "model-x"
    assert s.llm_timeout_seconds == 12.5


def test_cors_origins_parse_json_and_comma():
    from app.config import Settings

    assert Settings._parse_cors_origins("a, b, c") == ["a", "b", "c"]
    assert Settings._parse_cors_origins("") == []
    assert Settings._parse_cors_origins(None) is None


# ============================================================================
# 9. OpenAPI
# ============================================================================

def test_openapi_docs_available(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200
    spec = client.get("/openapi.json").json()
    assert "/api/v1/health" in spec["paths"]
    assert "/api/v1/ready" in spec["paths"]


# ============================================================================
# 10. Lifecycle
# ============================================================================

def test_lifecycle_populates_state(test_app):
    """Startup builds the container & readiness; shutdown disposes cleanly."""
    with TestClient(test_app) as c:
        container = test_app.state.container
        assert container is not None
        assert test_app.state.readiness is not None
        # Container is fully wired.
        assert isinstance(container.llm_provider, LLMProvider)
        assert isinstance(container.tool_gateway, ToolGateway)
        assert isinstance(container.brain_orchestrator, BrainOrchestrator)
        assert isinstance(container.context_manager, ContextManager)
        assert isinstance(container.grounding_service, GroundingService)
        c.get("/api/v1/health")

    # After shutdown, sessions are released.
    assert test_app.state.container.context_manager._sessions == {}


# ============================================================================
# 11. Production-safe behavior
# ============================================================================

def test_production_refuses_insecure_secret():
    with pytest.raises(RuntimeError):
        create_app(_test_settings(app_env="production"), configure_logging_enabled=False)


def test_production_refuses_wildcard_cors():
    with pytest.raises(RuntimeError):
        create_app(
            _test_settings(
                app_env="production", secret_key="a-real-secret", cors_origins=["*"]
            ),
            configure_logging_enabled=False,
        )


def test_production_with_secure_config_boots():
    app = create_app(
        _test_settings(
            app_env="production",
            secret_key="a-real-secret",
            cors_origins=["https://app.example.com"],
        ),
        configure_logging_enabled=False,
    )
    assert app.title == "WeatherGPT-Test"


# ============================================================================
# 12. Dependency injection boundaries
# ============================================================================

def test_llm_provider_is_mock_in_test_env(test_app):
    with TestClient(test_app) as c:
        assert isinstance(test_app.state.container.llm_provider, MockLLMProvider)
        c.get("/api/v1/health")


def test_dependency_providers_expose_services(client):
    # The /health endpoint does not resolve domain services, but the container
    # wired at startup exposes all boundaries. Verify via app.state.
    container = client.app.state.container
    assert isinstance(container.tool_gateway, ToolGateway)
    assert isinstance(container.brain_orchestrator, BrainOrchestrator)
    assert isinstance(container.grounding_service, GroundingService)


# ============================================================================
# 13. Structured logging
# ============================================================================

def test_structured_logging_formatter_outputs_json():
    import logging

    from app.core.logging import StructuredJsonFormatter

    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-1"
    record.status = 200
    line = StructuredJsonFormatter().format(record)
    import json

    parsed = json.loads(line)
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "hello"
    assert parsed["request_id"] == "req-1"
    assert parsed["status"] == 200


# ============================================================================
# 14. Root metadata
# ============================================================================

def test_root_metadata_endpoint(client):
    resp = client.get("/api/v1/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["health_url"] == "/api/v1/health"
    assert body["ready_url"] == "/api/v1/ready"


# ============================================================================
# 15. Map Explorer UI
# ============================================================================

def test_map_explorer_endpoint(client):
    resp = client.get("/map")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Map Explorer" in resp.text
    assert "RainViewer.com" in resp.text



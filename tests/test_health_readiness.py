"""Targeted test suite for Milestone B13.11 — Health, Readiness & Dependency Monitoring.

Verifies:
1. /api/v1/health is ultra-lightweight, purely liveness, and never touches DB/providers.
2. /api/v1/ready evaluates registered readiness probes and aggregates status safely.
3. Database available reports status="ready" with PostGIS version.
4. Database unavailable reports status="not_ready" with safe details (zero connection strings).
5. External provider circuit breaker trip reports degraded provider metadata without failing application readiness.
6. Database recovery restores status="ready".
7. Zero secrets, credentials, or internal infrastructure topologies exposed in output payloads.
"""

from unittest.mock import AsyncMock, MagicMock
from httpx import ASGITransport, AsyncClient
import pytest

from app.adapters.circuit_breaker import CircuitBreaker, CircuitBreakerState
from app.adapters.strategy import WeatherProviderManager
from app.config import Settings
from app.core.factory import create_app
from app.core.readiness import ApplicationProbe, ProbeResult, ProviderHealthProbe, ReadinessChecker
from app.db.health import DatabaseProbe


@pytest.mark.asyncio
async def test_health_liveness_probe_isolated():
    """Verify /api/v1/health returns 200 healthy quickly without touching DB/external APIs."""
    test_settings = Settings(app_env="test", debug=False)
    app = create_app(settings=test_settings, configure_logging_enabled=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        payload = resp.json()

        assert payload["status"] == "healthy"
        assert payload["app_name"] == "WeatherGPT"
        assert payload["environment"] == "test"
        assert "timestamp" in payload


@pytest.mark.asyncio
async def test_readiness_database_available():
    """Verify /api/v1/ready reports ready when application and database probes succeed."""
    test_settings = Settings(app_env="test", debug=False)
    app = create_app(settings=test_settings, configure_logging_enabled=False)

    readiness = ReadinessChecker()
    readiness.register(ApplicationProbe())

    mock_db_probe = AsyncMock(spec=DatabaseProbe)
    mock_db_probe.name = "database"
    mock_db_probe.check.return_value = ProbeResult(
        name="database",
        ok=True,
        detail="database connected",
        metadata={"postgis": "3.4.0"},
    )
    readiness.register(mock_db_probe)
    app.state.readiness = readiness

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/ready")
        assert resp.status_code == 200
        payload = resp.json()

        assert payload["status"] == "ready"
        assert payload["ready"] is True
        assert payload["dependencies"]["application"]["status"] == "connected"
        assert payload["dependencies"]["database"]["status"] == "connected"
        assert payload["dependencies"]["database"]["postgis"] == "3.4.0"


@pytest.mark.asyncio
async def test_readiness_database_unavailable_not_ready():
    """Verify /api/v1/ready reports not_ready when database is down, without crashing."""
    test_settings = Settings(app_env="test", debug=False)
    app = create_app(settings=test_settings, configure_logging_enabled=False)

    readiness = ReadinessChecker()
    readiness.register(ApplicationProbe())

    mock_db_probe = AsyncMock(spec=DatabaseProbe)
    mock_db_probe.name = "database"
    mock_db_probe.check.return_value = ProbeResult(
        name="database",
        ok=False,
        detail="database unavailable",
        metadata={"postgis": "unavailable"},
    )
    readiness.register(mock_db_probe)
    app.state.readiness = readiness

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/ready")
        assert resp.status_code == 200
        payload = resp.json()

        assert payload["status"] == "not_ready"
        assert payload["ready"] is False
        assert payload["dependencies"]["database"]["status"] == "unavailable"
        assert "password" not in str(payload).lower()
        assert "postgres://" not in str(payload)


@pytest.mark.asyncio
async def test_readiness_provider_degradation_non_fatal():
    """Verify external provider circuit trip reports degraded status without failing readiness."""
    test_settings = Settings(app_env="test", debug=False)
    app = create_app(settings=test_settings, configure_logging_enabled=False)

    readiness = ReadinessChecker()
    readiness.register(ApplicationProbe())

    mock_manager = MagicMock(spec=WeatherProviderManager)
    mock_manager.get_circuit_status.return_value = {
        "open_meteo": {"state": "OPEN", "failures": 5, "last_failure": "Timeout"},
        "openweather": {"state": "CLOSED", "failures": 0},
    }

    readiness.register(ProviderHealthProbe(weather_manager=mock_manager))
    app.state.readiness = readiness

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/ready")
        assert resp.status_code == 200
        payload = resp.json()

        # Application is still considered ready because fallback providers exist
        assert payload["ready"] is True
        assert payload["status"] == "ready"
        provider_dep = payload["dependencies"]["providers"]
        assert "open_meteo" in provider_dep["detail"]


@pytest.mark.asyncio
async def test_readiness_database_recovery():
    """Verify /api/v1/ready dynamically updates when database transitions from down to up."""
    test_settings = Settings(app_env="test", debug=False)
    app = create_app(settings=test_settings, configure_logging_enabled=False)

    readiness = ReadinessChecker()
    readiness.register(ApplicationProbe())

    mock_db_probe = AsyncMock(spec=DatabaseProbe)
    mock_db_probe.name = "database"
    readiness.register(mock_db_probe)
    app.state.readiness = readiness

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Initially down
        mock_db_probe.check.return_value = ProbeResult(name="database", ok=False, detail="database down")
        resp1 = await client.get("/api/v1/ready")
        assert resp1.json()["ready"] is False

        # 2. Database recovers
        mock_db_probe.check.return_value = ProbeResult(name="database", ok=True, detail="database connected", metadata={"postgis": "3.4.0"})
        resp2 = await client.get("/api/v1/ready")
        assert resp2.json()["ready"] is True
        assert resp2.json()["status"] == "ready"

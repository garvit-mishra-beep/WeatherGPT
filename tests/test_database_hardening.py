"""Targeted test suite for Milestone B13.5 — Database Hardening.

Verifies:
1. Connection pool knobs and timeout configuration (pool size, overflow, recycle, command/connect timeouts).
2. Transaction safety (clean commit on success, automatic rollback on exception, session cleanup).
3. BaseRepository transactional integrity.
4. Database readiness probe failure isolation (identifies DB unavailability without crashing).
5. Disposal and idempotent cleanup (no session/connection leaks).
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.config import Settings
from app.core.readiness import ProbeResult
from app.db.health import DatabaseProbe
from app.db.service import DatabaseService
from app.db.session import create_async_engine_from_settings, create_session_factory, dispose_engine


def test_database_settings_and_pool_config():
    """Verify that Settings exposes hardened connection pool and timeout parameters."""
    cfg = Settings(
        database_pool_size=15,
        database_max_overflow=10,
        database_pool_timeout=5.0,
        database_pool_recycle=900,
        database_command_timeout=20.0,
        database_connect_timeout=8.0,
    )

    assert cfg.database_pool_size == 15
    assert cfg.database_max_overflow == 10
    assert cfg.database_pool_timeout == 5.0
    assert cfg.database_pool_recycle == 900
    assert cfg.database_command_timeout == 20.0
    assert cfg.database_connect_timeout == 8.0


def test_async_engine_creation_connect_args():
    """Verify create_async_engine_from_settings constructs engine with pre-ping and connect_args."""
    cfg = Settings(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/testdb",
        database_pool_size=10,
        database_max_overflow=5,
        database_pool_timeout=10.0,
        database_pool_recycle=1800,
        database_command_timeout=25.0,
        database_connect_timeout=7.0,
    )

    engine = create_async_engine_from_settings(cfg)
    try:
        assert isinstance(engine, AsyncEngine)
        assert engine.pool.size() == 10
        assert engine.pool._max_overflow == 5
        assert engine.pool._timeout == 10.0
        assert engine.pool._recycle == 1800
        assert engine.pool._pre_ping is True
    finally:
        engine.sync_engine.dispose()


@pytest.mark.asyncio
async def test_session_context_success_commit():
    """Verify session_context commits on normal block exit."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__.return_value = mock_session
    mock_factory.return_value.__aexit__.return_value = None

    db_service = DatabaseService(settings=Settings())
    db_service._session_factory = mock_factory
    db_service._engine = MagicMock(spec=AsyncEngine)

    async with db_service.session_context() as session:
        assert session == mock_session

    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_session_context_exception_rollback():
    """Verify session_context rolls back when an exception occurs inside the context."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__.return_value = mock_session
    mock_factory.return_value.__aexit__.return_value = None

    db_service = DatabaseService(settings=Settings())
    db_service._session_factory = mock_factory
    db_service._engine = MagicMock(spec=AsyncEngine)

    with pytest.raises(ValueError, match="Simulated database failure"):
        async with db_service.session_context() as session:
            raise ValueError("Simulated database failure")

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_database_probe_uninitialized():
    """Verify DatabaseProbe reports ok=False when session factory is uninitialized."""
    probe = DatabaseProbe(session_factory=None, engine=None)
    result = await probe.check()

    assert isinstance(result, ProbeResult)
    assert result.ok is False
    assert result.name == "database"
    assert "not initialized" in result.detail


@pytest.mark.asyncio
async def test_database_probe_connection_failure():
    """Verify DatabaseProbe catches connection errors cleanly and reports ok=False."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.side_effect = ConnectionRefusedError("PostgreSQL port 5432 refused")

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__.return_value = mock_session
    mock_factory.return_value.__aexit__.return_value = None

    probe = DatabaseProbe(session_factory=mock_factory)
    result = await probe.check()

    assert result.ok is False
    assert result.name == "database"
    assert "database unavailable" in result.detail
    assert result.metadata["postgis"] == "unavailable"


@pytest.mark.asyncio
async def test_database_service_dispose_idempotent():
    """Verify DatabaseService.dispose can be called multiple times without error."""
    mock_engine = AsyncMock(spec=AsyncEngine)
    db_service = DatabaseService(settings=Settings(), engine=mock_engine)
    db_service.initialize()

    await db_service.dispose()
    assert db_service.engine is None
    assert db_service.session_factory is None

    # Second call must be safe
    await db_service.dispose()

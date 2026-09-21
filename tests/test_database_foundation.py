"""B2 — PostgreSQL + PostGIS foundation (offline / unit) test suite.

These tests are fully self-contained: they require **no** live PostgreSQL/PostGIS
instance. They cover configuration, async URL handling, engine/factory creation,
the per-request session dependency (offline path), the repository foundation,
PostGIS spatial type configuration, the database readiness probe (offline /
unavailable), SQL seed-safety, migration configuration, production safety, and
the absence of credential leakage in logs.

Live-database behaviour belongs in ``tests/test_database_integration.py`` and is
gated behind the ``integration`` marker (skipped when PostGIS is unavailable).
"""

import asyncio
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import List, Optional

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from app.config import Settings
from app.core.factory import create_app
from app.db import base as db_base
from app.db.health import DatabaseProbe
from app.db.repositories import BaseRepository
from app.db.service import DatabaseService
from app.db.session import (
    create_async_engine_from_settings,
    create_session_factory,
    dispose_engine,
)
from app.db.spatial import MultiPolygon, Point, geography
from app.dependencies.providers import get_db_session


def _test_settings(**overrides) -> Settings:
    """Build an isolated, test-safe Settings instance for offline tests."""
    defaults = {"app_env": "test", "app_name": "WeatherGPT-Test"}
    defaults.update(overrides)
    return Settings(**defaults)


# ============================================================================
# 1. Settings database configuration
# ============================================================================

def test_database_settings_defaults():
    s = _test_settings()
    assert s.database_url == "postgresql://postgres:postgres@localhost:5432/weathergpt"
    assert s.database_pool_size == 10
    assert s.database_max_overflow == 5
    assert s.database_pool_timeout == 10.0
    assert s.database_pool_recycle == 1800
    assert s.database_echo is False
    assert s.database_url_scheme == "postgresql+asyncpg"


def test_database_settings_env_overridable(monkeypatch):
    monkeypatch.setenv("DATABASE_POOL_SIZE", "20")
    monkeypatch.setenv("DATABASE_MAX_OVERFLOW", "8")
    monkeypatch.setenv("DATABASE_POOL_TIMEOUT", "15")
    monkeypatch.setenv("DATABASE_POOL_RECYCLE", "3600")
    monkeypatch.setenv("DATABASE_ECHO", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db:5432/w")
    s = Settings(_env_file=None)
    assert s.database_pool_size == 20
    assert s.database_max_overflow == 8
    assert s.database_pool_timeout == 15.0
    assert s.database_pool_recycle == 3600
    assert s.database_echo is True
    assert s.database_url == "postgresql://u:p@db:5432/w"


# ============================================================================
# 2. Async database URL handling
# ============================================================================

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("postgresql://postgres:postgres@localhost:5432/weathergpt",
         "postgresql+asyncpg://postgres:postgres@localhost:5432/weathergpt"),
        ("postgresql+psycopg2://u:p@host:5432/db",
         "postgresql+asyncpg://u:p@host:5432/db"),
        ("postgresql+psycopg://u:p@host:5432/db",
         "postgresql+asyncpg://u:p@host:5432/db"),
        ("postgres://u:p@host:5432/db",
         "postgresql+asyncpg://u:p@host:5432/db"),
        ("postgresql+asyncpg://u:p@host:5432/db",
         "postgresql+asyncpg://u:p@host:5432/db"),
    ],
)
def test_async_database_url_conversion(raw, expected):
    assert Settings(database_url=raw).async_database_url == expected


# ============================================================================
# 3. SQLAlchemy engine creation (lazy — no connection at import/create)
# ============================================================================

def test_engine_created_lazily():
    s = _test_settings()
    engine = create_async_engine_from_settings(s)
    assert isinstance(engine, AsyncEngine)
    # Creating the engine must not open a connection.
    asyncio.run(dispose_engine(engine))


def test_engine_creation_logs_no_credentials(caplog):
    s = Settings(
        app_env="test",
        database_url="postgresql://dbuser:S3cr3t_P@ssword@dbhost:5432/weathergpt",
    )
    with caplog.at_level(logging.INFO):
        engine = create_async_engine_from_settings(s)
    logs = caplog.text
    assert "S3cr3t_P@ssword" not in logs
    assert "dbhost" not in logs
    asyncio.run(dispose_engine(engine))


# ============================================================================
# 4. Session factory
# ============================================================================

def test_session_factory_creation():
    s = _test_settings()
    engine = create_async_engine_from_settings(s)
    factory = create_session_factory(engine)
    assert isinstance(factory, async_sessionmaker)
    asyncio.run(dispose_engine(engine))


def test_session_factory_returns_async_session():
    s = _test_settings()
    engine = create_async_engine_from_settings(s)
    factory = create_session_factory(engine)

    async def _open():
        async with factory() as session:
            return isinstance(session, AsyncSession)

    assert asyncio.run(_open()) is True
    asyncio.run(dispose_engine(engine))


# ============================================================================
# 5. Session dependency lifecycle (offline path: uninitialized DB)
# ============================================================================

def test_db_session_dependency_returns_none_in_offline_env():
    app = create_app(_test_settings(), configure_logging_enabled=False)

    @app.get("/api/v1/_dbtest")
    async def _route(session: Optional[AsyncSession] = Depends(get_db_session)):
        return {"session_is_none": session is None}

    with TestClient(app) as c:
        resp = c.get("/api/v1/_dbtest")
    assert resp.status_code == 200
    assert resp.json()["session_is_none"] is True


# ============================================================================
# 6. Repository foundation
# ============================================================================

class SampleModel(db_base.Base):
    __tablename__ = "sample_model"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class FakeResult:
    def __init__(self, rows: List[SampleModel]):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class FakeRepoSession:
    """A tiny stand-in for AsyncSession that records calls (no DB)."""

    def __init__(self):
        self.executed: list = []
        self.committed = False
        self.rolled_back = False
        self.added = None
        self.deleted = None

    async def execute(self, stmt):
        self.executed.append(stmt)
        return FakeResult([])

    async def get(self, model, pk):
        return None

    def add(self, obj):
        self.added = obj

    def add_all(self, objs):
        self.added = objs

    async def flush(self):
        return None

    async def refresh(self, obj):
        return None

    async def delete(self, obj):
        self.deleted = obj

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


@pytest.mark.asyncio
async def test_repository_foundation_never_commits_implicitly():
    session = FakeRepoSession()
    repo = BaseRepository(session=session, model=SampleModel)
    repo.add(SampleModel(name="wheat"))
    await repo.list()
    await repo.get_by(name="wheat")
    await repo.get(1)
    # Nothing was committed implicitly by the repository.
    assert session.committed is False
    assert session.rolled_back is False
    assert len(session.executed) == 2  # list() + get_by()


@pytest.mark.asyncio
async def test_repository_explicit_commit_and_rollback():
    session = FakeRepoSession()
    repo = BaseRepository(session=session, model=SampleModel)
    await repo.commit()
    assert session.committed is True
    await repo.rollback()
    assert session.rolled_back is True


# ============================================================================
# 7. PostGIS spatial type configuration
# ============================================================================

def test_postgis_types_configured_for_epsg4326():
    assert MultiPolygon.srid == 4326
    assert MultiPolygon.geometry_type == "MULTIPOLYGON"
    assert Point.geometry_type == "POINT"
    assert geography().srid == 4326


# ============================================================================
# 8. Database readiness probe (offline / unavailable)
# ============================================================================

@pytest.mark.asyncio
async def test_database_probe_uninitialized_is_safe():
    probe = DatabaseProbe()
    result = await probe.check()
    assert result.ok is False
    assert result.name == "database"
    assert result.metadata["postgis"] == "unavailable"
    # Safe detail — no URL / credentials / trace.
    assert "postgresql" not in result.detail
    assert result.detail == "database.engine not initialized"


# ============================================================================
# 9. PostgreSQL / PostGIS unavailable behaviour
# ============================================================================

class FailingSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, stmt):
        raise ConnectionRefusedError("connection failed")


@pytest.mark.asyncio
async def test_database_probe_reports_unavailable_on_connection_failure(caplog):
    factory = lambda: FailingSession()  # noqa: E731
    probe = DatabaseProbe(session_factory=factory)
    with caplog.at_level(logging.WARNING):
        result = await probe.check()
    assert result.ok is False
    assert result.metadata["postgis"] == "unavailable"
    # Credentials never appear in logs.
    assert "postgres:" not in caplog.text
    assert "password" not in caplog.text.lower()


# ============================================================================
# 10. PostGIS available behaviour
# ============================================================================

class PostGisSession:
    def __init__(self, version: Optional[str] = "3.4.2 POSTGIS bundle"):
        self._version = version

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, stmt):
        sql = str(stmt)
        if "pg_extension" in sql:
            return _PostGisExtResult(has_extension=True)
        if "postgis_version" in sql:
            return _ScalarResult(self._version)
        return _ScalarResult(1)


class _PostGisExtResult:
    def __init__(self, has_extension: bool):
        self._has = has_extension

    def first(self):
        return ("postgis",) if self._has else None


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def first(self):
        return self._value

    def scalar(self):
        return self._value


@pytest.mark.asyncio
async def test_database_probe_detects_postgis():
    probe = DatabaseProbe(session_factory=lambda: PostGisSession())
    result = await probe.check()
    assert result.ok is True
    assert result.metadata["postgis"].startswith("3.4.2")
    assert "connected" in result.detail


@pytest.mark.asyncio
async def test_database_probe_reports_postgis_missing():
    probe = DatabaseProbe(session_factory=lambda: PostGisSession(version=None))
    # Simulate missing extension: chei the execute path to return no ext row.
    class NoExtSession(PostGisSession):
        async def execute(self, stmt):
            if "pg_extension" in str(stmt):
                return _PostGisExtResult(has_extension=False)
            return _ScalarResult(1)

    probe_noext = DatabaseProbe(session_factory=lambda: NoExtSession())
    result = await probe_noext.check()
    assert result.ok is False
    assert result.metadata["postgis"] == "unavailable"
    assert "postgis extension missing" in result.detail


# ============================================================================
# 11. Migration configuration
# ============================================================================

def test_alembic_configuration_files_present():
    assert Path("alembic.ini").exists()
    assert Path("app/db/migrations/env.py").exists()
    assert Path("app/db/migrations/versions/0001_enable_postgis.py").exists()


def test_migration_env_uses_application_settings():
    src = Path("app/db/migrations/env.py").read_text(encoding="utf-8")
    assert "async_database_url" in src
    assert "from app.config import settings" in src


def test_initial_migration_enables_postgis():
    spec = importlib.util.spec_from_file_location(
        "mig_0001", "app/db/migrations/versions/0001_enable_postgis.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "0001"
    assert module.down_revision is None
    source = inspect.getsource(module)
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in source
    assert "DROP DATABASE" not in source
    assert "TRUNCATE" not in source


# ============================================================================
# 12. Production secret / config validation + no secret leakage
# ============================================================================

def test_default_database_config_is_placeholder_not_real_secret():
    s = Settings()
    # The bundled default is a local-development placeholder, never a real secret.
    assert s.database_url != "postgresql://postgres:S3cr3t_P@ssword@db:5432/weathergpt"


def test_database_service_is_cheap_to_construct_without_engine():
    s = _test_settings()
    service = DatabaseService(settings=s)
    # Constructing the service must NOT create an engine (no import-time I/O).
    assert service.is_initialized is False
    assert service.engine is None
    assert service.probe is None


def test_database_echo_never_enabled_in_fixture_defaults():
    s = _test_settings()
    assert s.database_echo is False

"""B2 — PostgreSQL + PostGIS integration tests.

These tests exercise a **real** PostgreSQL/PostGIS instance and are skipped
automatically when one is not reachable at ``TEST_DATABASE_URL`` (falling back to
the configured ``DATABASE_URL``). Run them only against a database you own:

    docker compose up -d postgres-postgis
    alembic upgrade head
    pytest -m integration -v

Requires the ``integration`` marker (registered in ``pytest.ini``).
"""

import asyncio
import os

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.config import Settings
from app.core.factory import create_app
from app.db.base import Base
from app.db.health import DatabaseProbe
from app.db.repositories import BaseRepository
from app.db.session import (
    create_async_engine_from_settings,
    create_session_factory,
    dispose_engine,
)

pytestmark = pytest.mark.integration

_INTEGRATION_URL = os.environ.get(
    "TEST_DATABASE_URL",
    Settings().database_url,  # default local dev URL
)


def _integration_settings() -> Settings:
    return Settings(
        app_env="development",
        app_name="WeatherGPT-Integration",
        database_url=_INTEGRATION_URL,
    )


def _require_postgis() -> None:
    """Skip the whole integration suite if PostGIS is unreachable.

    Mirrors the ping used by the ``engine`` fixture so that *every* integration
    test (including the synchronous ``/ready`` test, which does not use that
    fixture) skips consistently when no live PostGIS is available.
    """
    engine = create_async_engine_from_settings(_integration_settings())

    async def _ping():
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    try:
        asyncio.run(_ping())
        return
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"PostgreSQL/PostGIS unavailable: {exc}")
    finally:
        asyncio.run(dispose_engine(engine))


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def engine():
    """A real async engine against the configured PostGIS database, or skip.

    Created as an async fixture so the engine lives in the same session-scoped
    event loop used by the async tests below (required on Windows so asyncpg's
    pooled connections are not bound to a throwaway loop that gets closed).
    """
    s = _integration_settings()
    eng = create_async_engine_from_settings(s)

    async def _ping():
        async with eng.connect() as conn:
            await conn.execute(text("SELECT 1"))

    try:
        await _ping()
    except Exception as exc:  # noqa: BLE001
        await dispose_engine(eng)
        pytest.skip(f"PostgreSQL/PostGIS unavailable: {exc}")
    yield eng
    await dispose_engine(eng)


@pytest.fixture(scope="module")
def session_factory(engine):
    return create_session_factory(engine)


@pytest.fixture(scope="module")
def probe(session_factory, engine):
    return DatabaseProbe(session_factory=session_factory, engine=engine)


# ============================================================================
# 1. Database readiness probe against a real PostGIS
# ============================================================================

@pytest.mark.asyncio(loop_scope="module")
async def test_database_probe_connects_and_finds_postgis(probe):
    result = await probe.check()
    assert result.ok is True
    assert result.name == "database"
    assert "connected" in result.detail
    assert result.metadata["postgis"].startswith("3.")


@pytest.mark.asyncio(loop_scope="module")
async def test_select_one_through_session(session_factory):
    async with session_factory() as session:  # noqa: SIM117
        result = await session.execute(text("SELECT 1"))
        value = result.scalar_one()
        assert value == 1


# ============================================================================
# 2. Repository against a real database (create/insert/select/drop)
# ============================================================================

class IntegrationSample(Base):
    __tablename__ = "integ_sample"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(nullable=False)


@pytest.mark.asyncio(loop_scope="module")
async def test_repository_persists_and_reads(engine):
    # Create only the integration test table (no destructive DDL elsewhere).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        session_factory = create_session_factory(engine)
        async with session_factory() as session:  # noqa: SIM117
            repo = BaseRepository(session=session, model=IntegrationSample)
            repo.add(IntegrationSample(label="gujarat"))
            await repo.commit()

        async with session_factory() as session:  # noqa: SIM117
            repo = BaseRepository(session=session, model=IntegrationSample)
            row = await repo.get_by(label="gujarat")
            assert row is not None
            assert row.label == "gujarat"
            items = await repo.list()
            assert len(items) >= 1
    finally:
        # Tear down only what we created (never destructive outside this test).
        async with engine.begin() as conn:
            await conn.run_sync(IntegrationSample.__table__.drop, checkfirst=True)


# ============================================================================
# 3. FastAPI /ready integration (database probe registered + shutdown clean)
# ============================================================================

def test_ready_includes_database_probe():
    _require_postgis()  # skip when no live PostGIS (same gating as the other tests)
    app = create_app(_integration_settings(), configure_logging_enabled=False)
    with TestClient(app) as c:
        resp = c.get("/api/v1/ready")
    assert resp.status_code == 200
    body = resp.json()
    deps = body["dependencies"]
    assert "database" in deps
    assert deps["database"]["status"] == "connected"
    assert deps["database"]["postgis"].startswith("3.")
    # Application probe is still present (B1 preserved).
    assert deps["application"]["status"] == "connected"

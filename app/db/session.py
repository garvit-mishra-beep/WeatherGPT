"""Async SQLAlchemy engine and session factory for PostgreSQL + PostGIS.

Key guarantees:

* **No connections at import time.**  Importing this module (or any ``app.db``
  module) never creates a database connection. Engines are created lazily when
  :func:`create_async_engine_from_settings` is called during application
  lifespan startup.
* **Async / asyncpg only.**  The engine always uses the proper
  ``postgresql+asyncpg`` URL (derived automatically from config).
* **Configurable pooling.**  pool size, max overflow, timeout and recycle are
  driven by settings.
* **Graceful disposal** via :func:`dispose_engine`.
"""

import logging
import uuid
from typing import Optional

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings

logger = logging.getLogger(__name__)


def create_async_engine_from_settings(settings: Settings) -> AsyncEngine:
    """Build a lazy, configured SQLAlchemy ``AsyncEngine`` for the app settings.

    No connection is opened here; the pool is created lazily on first use.

    Args:
        settings: Application settings (``async_database_url`` + pool knobs).

    Returns:
        AsyncEngine: configured asyncpg engine targeting PostgreSQL/PostGIS.
    """
    url = settings.async_database_url
    logger.info(
        "Creating async database engine (pool_size=%s, max_overflow=%s, "
        "pool_timeout=%s, pool_recycle=%s, echo=%s)",
        settings.database_pool_size,
        settings.database_max_overflow,
        settings.database_pool_timeout,
        settings.database_pool_recycle,
        settings.database_echo,
    )
    engine = create_async_engine(
        url,
        echo=settings.database_echo,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        pool_recycle=settings.database_pool_recycle,
        pool_pre_ping=True,
        future=True,
        # Never log the URL (it can contain credentials).
        hide_parameters=True,
    )

    if settings.database_echo:
        _attach_sql_logger(engine.sync_engine)

    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Return an ``async_sessionmaker`` bound to the given engine.

    Sessions created from this factory are transactional; callers (or the
    per-request dependency) are responsible for commit/rollback and close.

    Args:
        engine: The async engine to bind.

    Returns:
        async_sessionmaker[AsyncSession]: a configured session factory.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def dispose_engine(engine: Optional[AsyncEngine]) -> None:
    """Gracefully close the engine and its connection pool.

    Safe to call multiple times and with ``None`` (e.g. when no engine was ever
    created for an environment). Does **not** drop any database objects.
    """
    if engine is None:
        return
    try:
        await engine.dispose()
        logger.info("Async database engine disposed")
    except Exception:  # noqa: BLE001 - shutdown must never mask prior work
        logger.exception("Error while disposing the async database engine")


def _attach_sql_logger(engine: Engine) -> None:
    """Log a bound-parameter-safe version of SQL statements when echo is on."""

    @event.listens_for(engine, "before_cursor_execute")
    def _log_sql(conn, cursor, statement, parameters, context, executemany):
        try:
            safe_statement = _redact_bind_parameters(statement, parameters)
            logger.debug("SQL: %s", safe_statement)
        except Exception:  # noqa: BLE001 - logging must never break a query
            pass


def _redact_bind_parameters(statement: str, parameters) -> str:
    """Return a SQL string without inline values (avoids credential leakage).

    A cheap, safe fallback: just clamp parameter length and never include bound
    values verbatim on the same line as the statement.
    """
    return statement.strip()[:2000]


def new_transaction_id() -> str:
    """Return a short unique identifier for a unit of transactional work."""
    return uuid.uuid4().hex[:12]

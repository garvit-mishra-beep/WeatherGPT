"""Database service owned by the application container.

The :class:`DatabaseService` is the single ownership boundary for the async
engine, the session factory and the database readiness probe. It is created
during application lifespan startup (from ``app.dependencies.container``), owns
no credentials, and is disposed cleanly on shutdown.

This boundary keeps FastAPI routes free of direct SQLAlchemy usage: routes depend
on an ``AsyncSession`` (via ``get_db_session``) or on ``DatabaseService`` itself.
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from app.config import Settings
from app.db.health import DatabaseProbe
from app.db.session import (
    create_async_engine_from_settings,
    create_session_factory,
    dispose_engine,
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """Owns the async engine, session factory and readiness probe for one app.

    Args:
        settings: Application settings used to construct the engine and factory.
        engine: Optional prebuilt async engine (tests may inject a fake).

    The engine is created lazily in :meth:`initialize`, which is only ever invoked
    during application startup — never at import time.
    """

    def __init__(
        self,
        settings: Settings,
        engine: Optional[AsyncEngine] = None,
    ) -> None:
        self._settings = settings
        self._engine = engine
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._probe: Optional[DatabaseProbe] = None

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def is_initialized(self) -> bool:
        return self._engine is not None

    def initialize(self) -> None:
        """Create the engine + session factory + probe if not already done."""
        if self._engine is None:
            self._engine = create_async_engine_from_settings(self._settings)
        if self._session_factory is None:
            self._session_factory = create_session_factory(self._engine)
        if self._probe is None:
            self._probe = DatabaseProbe(
                session_factory=self._session_factory, engine=self._engine
            )
        logger.info("DatabaseService initialized")

    @property
    def engine(self) -> Optional[AsyncEngine]:
        return self._engine

    @property
    def session_factory(self) -> Optional[async_sessionmaker[AsyncSession]]:
        return self._session_factory

    @property
    def probe(self) -> Optional[DatabaseProbe]:
        return self._probe

    async def session_context(self):
        """Asynchronous context manager yielding a bound ``AsyncSession``.

        The caller manages transaction lifecycle; the context only guarantees the
        session is closed on exit.
        """
        if self._session_factory is None:
            raise RuntimeError("DatabaseService is not initialized")
        async with self._session_factory() as session:
            yield session

    async def dispose(self) -> None:
        """Gracefully dispose the engine and pool (idempotent)."""
        await dispose_engine(self._engine)
        self._engine = None
        self._session_factory = None
        self._probe = None

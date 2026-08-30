"""Database readiness probing (PostgreSQL connectivity + PostGIS availability).

The :class:`DatabaseProbe` is a lightweight readiness probe that:

1. checks PostgreSQL connectivity with ``SELECT 1``,
2. runs a basic query execution,
3. verifies the PostGIS extension and reads its version.

It intentionally avoids expensive queries and never surfaces credentials, the
connection URL, or internal tracebacks. If the database is unreachable the probe
reports ``ok=False`` with a safe message and ``/ready`` returns ``not_ready``.
"""

import logging
from typing import AsyncIterator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from app.core.readiness import ProbeResult

logger = logging.getLogger(__name__)

_SELECT_ONE = text("SELECT 1")
_POSTGIS_AVAILABLE = text("SELECT extname FROM pg_extension WHERE extname = 'postgis'")
_POSTGIS_VERSION = text("SELECT postgis_version()")


class DatabaseProbe:
    """Readiness probe for PostgreSQL connectivity and PostGIS availability.

    Attributes:
        name: Readiness probe identifier (``"database"``) shown in ``/ready``.
    """

    name: str = "database"

    def __init__(
        self,
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
        engine: Optional[AsyncEngine] = None,
    ) -> None:
        """Construct the probe from a session factory and/or an engine.

        At least one of ``session_factory`` or ``engine`` must be provided. If only
        ``engine`` is given, a transient session factory is derived from it.
        """
        self._session_factory = session_factory or (
            async_sessionmaker(bind=engine, expire_on_commit=False) if engine else None
        )

    async def check(self) -> ProbeResult:
        """Run the database readiness checks and return a structured result.

        Returns:
            ProbeResult: ``ok=True`` when the database answers ``SELECT 1`` and
            PostGIS is present; otherwise ``ok=False`` with a safe detail. The
            PostGIS version/state is carried in ``metadata["postgis"]``.
        """
        if self._session_factory is None:
            return ProbeResult(
                name=self.name,
                ok=False,
                detail="database.engine not initialized",
                metadata={"postgis": "unavailable"},
            )

        try:
            async with self._session_factory() as session:
                return await self._check_with_session(session)
        except Exception as exc:  # noqa: BLE001 - probe must never crash /ready
            logger.warning("Database readiness probe failed: %s", exc)
            return ProbeResult(
                name=self.name,
                ok=False,
                detail="database unavailable",
                metadata={"postgis": "unavailable"},
            )

    async def _check_with_session(self, session: AsyncSession) -> ProbeResult:
        # 1) Connectivity + basic query execution.
        await session.execute(_SELECT_ONE)
        # 2) PostGIS presence.
        ext_row = (await session.execute(_POSTGIS_AVAILABLE)).first()
        if ext_row is None:
            return ProbeResult(
                name=self.name,
                ok=False,
                detail="postgis extension missing",
                metadata={"postgis": "unavailable"},
            )
        # 3) PostGIS version.
        version_row = (await session.execute(_POSTGIS_VERSION)).scalar()
        postgis = str(version_row) if version_row else "available"
        return ProbeResult(
            name=self.name,
            ok=True,
            detail="database connected",
            metadata={"postgis": postgis},
        )

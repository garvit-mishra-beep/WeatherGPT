"""Minimal generic async repository foundation.

A deliberately small base class that future repositories
(``BoundaryRepository``, ``WeatherRepository``, ``NWPRepository``,
``HazardRepository``, ``AnalyticsRepository``) can extend. It provides basic
single-entity operations without building a heavy generic framework and without
introducing hidden commits.
"""

from typing import Generic, List, Optional, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import InstrumentedAttribute

from app.db.base import Base

T = TypeVar("T", bound=Base)

# SQLAlchemy's scalar primary keys (int, UUID, str) are accepted as query keys.
PK = object


class BaseRepository(Generic[T]):
    """Statically-typed base repository bound to a single ORM model.

    Transaction semantics
    ----------------------
    * Repositories **never** commit implicitly. ``commit()`` is an explicit,
      deliberate call made by the caller (service layer or transaction boundary).
    * ``add`` / ``add_all`` / ``delete`` only stage changes on the session.
    * ``flush`` pushes staged SQL to the transaction (assigning generated PKs)
      without committing — callers that need generated IDs may flush.
    * On errors the caller (or the request-scoped dependency) rolls back so a
      failed transaction does not poison the pooled connection.
    * Sessions are scoped to a single request (see ``get_db_session``); they are
      closed by the dependency after the response.
    """

    def __init__(self, session: AsyncSession, model: Type[T]) -> None:
        self.session = session
        self.model = model

    async def get(self, primary_key: PK) -> Optional[T]:
        """Return a single entity by primary key, or ``None``."""
        return await self.session.get(self.model, primary_key)

    async def list(self, limit: Optional[int] = None) -> Sequence[T]:
        """Return all rows matching no filter (bounded by ``limit`` when given)."""
        stmt = select(self.model)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by(self, **kwargs: object) -> Optional[T]:
        """Return the first row matching all equality filters, or ``None``."""
        result = await self.session.execute(select(self.model).filter_by(**kwargs))
        return result.scalars().first()

    def add(self, obj: T) -> None:
        """Stage an entity for insert/update (no commit)."""
        self.session.add(obj)

    def add_all(self, objs: Sequence[T]) -> None:
        """Stage multiple entities (no commit)."""
        self.session.add_all(list(objs))

    async def flush(self) -> None:
        """Push staged SQL to the transaction without committing."""
        await self.session.flush()

    async def refresh(self, obj: T) -> None:
        """Expire and reload the entity's attributes from the database."""
        await self.session.refresh(obj)

    async def delete(self, obj: T) -> None:
        """Stage an entity for deletion (no commit)."""
        await self.session.delete(obj)

    async def commit(self) -> None:
        """Explicitly commit the current transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Roll back the current transaction and clear staged state.

        Safe to call after a failure; it also neutralises any left-over state so
        the session (and its pooled connection) can be reused safely.
        """
        await self.session.rollback()

"""SQLAlchemy declarative foundation for the WeatherGPT PostgreSQL/PostGIS layer.

The declarative base and reusable mixins live here. This module has **no side
effects** on import: it does not create engines, connect, or read configuration.
Database resources are initialised only during application lifespan startup
(see :mod:`app.db.session` and :mod:`app.db.service`).
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Application-wide declarative base.

    All ORM models in ``app.db.models`` inherit from this. The PostGIS extension
    is enabled through an Alembic migration (``CREATE EXTENSION IF NOT EXISTS
    postgis``) and is not an implicit part of the Python metadata. Tables default
    to the ``public`` PostgreSQL schema.
    """


class TimestampMixin:
    """Adds timezone-aware ``created_at`` / ``updated_at`` columns.

    Use only where the schema specification (``docs/10``) actually requires these
    fields; many reference/spatial tables (e.g. ``spatial_states``) do **not**.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="UTC time of row creation",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="UTC time of last update",
    )

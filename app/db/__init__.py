"""WeatherGPT PostgreSQL + PostGIS database foundation (B2).

Provides:

* :class:`app.db.base.Base` — the shared declarative base + timestamp mixin.
* :mod:`app.db.session` — async engine / session factory / lifecycle helpers.
* :mod:`app.db.spatial` — reusable PostGIS geometry/geography type helpers (EPSG:4326).
* :mod:`app.db.health` — the database readiness probe (PostgreSQL + PostGIS).
* :mod:`app.db.service` — the application-owned ``DatabaseService`` boundary.
* :mod:`app.db.repositories` — a minimal async repository foundation.
* :mod:`app.db.migrations` — Alembic migration definitions (incl. PostGIS enable).

This module performs **no I/O at import time**: engines are created lazily during
application startup, never on ``import``.
"""

from app.db.base import Base, TimestampMixin

__all__ = ["Base", "TimestampMixin"]

"""ORM models package for WeatherGPT.

Re-exports all database models so metadata is discovered cleanly by Alembic
and application repositories.
"""

from app.db.models.boundaries import (
    SpatialCountry,
    SpatialDistrict,
    SpatialState,
    SpatialSubDistrict,
)

__all__ = [
    "SpatialCountry",
    "SpatialState",
    "SpatialDistrict",
    "SpatialSubDistrict",
]

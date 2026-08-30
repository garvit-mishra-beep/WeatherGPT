"""Application repository layer.

B2 provides the *foundation* — a minimal generic :class:`BaseRepository`
(:mod:`app.db.repositories.base`) — that future repositories extend:

* ``BoundaryRepository``    (B3 boundaries)
* ``WeatherRepository``     (weather ingest)
* ``NWPRepository``         (B5 NWP grids)
* ``HazardRepository``      (GIS hazard layers)
* ``AnalyticsRepository``   (analytics)

None of those domain repositories are implemented yet.
"""

from app.db.repositories.base import BaseRepository

__all__ = ["BaseRepository"]

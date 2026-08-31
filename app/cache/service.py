"""Resilient Cache Service wrapper.

Guarantees:
- Cache failures (reads/writes/backend exceptions) NEVER crash the application.
- On cache get failure, returns None (transparent cache miss).
- On cache set failure, logs a warning and returns gracefully.
- Configurable default TTLs per domain.
"""

import logging
from typing import Any, Optional

from app.cache.base import CacheBackend
from app.cache.memory import InMemoryCacheBackend

logger = logging.getLogger(__name__)

# Standard domain TTL configurations (seconds)
TTL_CURRENT_WEATHER = 300.0   # 5 minutes
TTL_FORECAST = 1800.0          # 30 minutes
TTL_ALERTS = 180.0             # 3 minutes
TTL_GIS_BOUNDARY = 86400.0     # 24 hours
TTL_NWP_GRID = 3600.0          # 1 hour


class CacheService:
    """Application-level cache service providing fault-tolerant caching."""

    def __init__(self, backend: Optional[CacheBackend] = None) -> None:
        self.backend = backend or InMemoryCacheBackend()

    async def get(self, key: str) -> Optional[Any]:
        """Safely retrieve item from cache backend. Returns None on error or miss."""
        try:
            return await self.backend.get(key)
        except Exception as exc:
            logger.warning("Cache GET failed for key '%s': %s (continuing to source)", key, exc)
            return None

    async def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        """Safely write item to cache backend. Never raises exceptions."""
        try:
            await self.backend.set(key, value, ttl_seconds=ttl_seconds)
        except Exception as exc:
            logger.warning("Cache SET failed for key '%s': %s (ignoring cache failure)", key, exc)

    async def delete(self, key: str) -> bool:
        """Safely delete item from cache backend."""
        try:
            return await self.backend.delete(key)
        except Exception as exc:
            logger.warning("Cache DELETE failed for key '%s': %s", key, exc)
            return False

    async def exists(self, key: str) -> bool:
        """Safely check key existence in cache backend."""
        try:
            return await self.backend.exists(key)
        except Exception as exc:
            logger.warning("Cache EXISTS failed for key '%s': %s", key, exc)
            return False

    async def clear(self) -> None:
        """Safely clear entire cache backend."""
        try:
            await self.backend.clear()
        except Exception as exc:
            logger.warning("Cache CLEAR failed: %s", exc)

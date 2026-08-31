"""Abstract base interface for WeatherGPT caching backends."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class CacheBackend(ABC):
    """Abstract protocol for cache implementations (in-memory, Redis, etc.)."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a value by key if present and not expired."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        """Store a value with a bounded TTL in seconds."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete an entry by key. Returns True if existed and deleted."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if an unexpired key exists."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Remove all cached entries."""
        pass

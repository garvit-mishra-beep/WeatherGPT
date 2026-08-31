"""Thread-safe In-Memory Cache Backend with TTL eviction."""

import asyncio
import time
from typing import Any, Dict, Optional, Tuple

from app.cache.base import CacheBackend


class InMemoryCacheBackend(CacheBackend):
    """Asynchronous, thread-safe in-memory cache with bounded TTL enforcement."""

    def __init__(self, default_ttl_seconds: float = 300.0, max_entries: int = 10000) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self.max_entries = max_entries
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._store:
                return None
            value, expiry = self._store[key]
            if time.perf_counter() < expiry:
                return value
            # Expired
            del self._store[key]
            return None

    async def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        expiry = time.perf_counter() + max(0.01, ttl)
        async with self._lock:
            # Capacity guard: prune oldest expired entry or pop if over limit
            if len(self._store) >= self.max_entries and key not in self._store:
                now = time.perf_counter()
                expired_keys = [k for k, (_, exp) in self._store.items() if now >= exp]
                if expired_keys:
                    for k in expired_keys[:100]:
                        del self._store[k]
                if len(self._store) >= self.max_entries:
                    # Evict oldest entry
                    first_key = next(iter(self._store))
                    del self._store[first_key]

            self._store[key] = (value, expiry)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    async def exists(self, key: str) -> bool:
        async with self._lock:
            if key not in self._store:
                return False
            _, expiry = self._store[key]
            if time.perf_counter() < expiry:
                return True
            del self._store[key]
            return False

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)

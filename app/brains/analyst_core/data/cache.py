"""TTL Cache for weather observations and forecasts."""

import hashlib
import json
import time
from typing import Any, Optional, Dict


class TTLCache:
    """Thread-safe time-to-live cache for API responses."""

    def __init__(self, default_ttl_seconds: int = 900):
        self.default_ttl = default_ttl_seconds
        self._store: Dict[str, Dict[str, Any]] = {}

    def _make_key(self, prefix: str, **kwargs: Any) -> str:
        """Generates deterministic cache key from parameters."""
        serialized = json.dumps(kwargs, sort_keys=True, default=str)
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
        return f"{prefix}:{digest}"

    def get(self, prefix: str, **kwargs: Any) -> Optional[Any]:
        """Retrieves cached item if not expired."""
        key = self._make_key(prefix, **kwargs)
        entry = self._store.get(key)
        if not entry:
            return None
        if time.time() > entry["expires_at"]:
            del self._store[key]
            return None
        return entry["value"]

    def set(self, prefix: str, value: Any, ttl_seconds: Optional[int] = None, **kwargs: Any) -> None:
        """Stores item with expiry."""
        key = self._make_key(prefix, **kwargs)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        self._store[key] = {
            "value": value,
            "expires_at": time.time() + ttl,
            "created_at": time.time(),
        }

    def clear(self) -> None:
        """Clears all cached entries."""
        self._store.clear()

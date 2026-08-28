"""In-memory deterministic tool result cache and deduplicator with TTL enforcement."""

import hashlib
import json
import time
from typing import Any, Dict, Optional, Tuple

from app.contracts.tool import ToolCallRequest, ToolCallResponse


class ToolResultCache:
    """Provides thread-safe caching and deduplication for deterministic tool calls."""

    def __init__(self, default_ttl_seconds: float = 300.0) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self._store: Dict[str, Tuple[ToolCallResponse, float]] = {}

    @staticmethod
    def generate_cache_key(request: ToolCallRequest) -> str:
        """Generates deterministic SHA-256 cache key from tool name and canonical arguments."""
        canonical_args = json.dumps(request.arguments, sort_keys=True)
        raw_key = f"{request.tool_name}:{canonical_args}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def get(self, request: ToolCallRequest) -> Optional[ToolCallResponse]:
        """Retrieves cached response if key exists and has not expired."""
        key = self.generate_cache_key(request)
        if key in self._store:
            response, expiry = self._store[key]
            if time.perf_counter() < expiry:
                # Return response with original call_id swapped for current request
                return response.model_copy(update={"call_id": request.call_id})
            else:
                del self._store[key]
        return None

    def set(
        self,
        request: ToolCallRequest,
        response: ToolCallResponse,
        ttl_seconds: Optional[float] = None,
    ) -> None:
        """Stores a successful tool execution response with a specified TTL."""
        if response.status != "success":
            return  # Never cache errors or failed executions

        key = self.generate_cache_key(request)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        expiry = time.perf_counter() + ttl
        self._store[key] = (response, expiry)

    def clear(self) -> None:
        """Flushes all entries from cache."""
        self._store.clear()

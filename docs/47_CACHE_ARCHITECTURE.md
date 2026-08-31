# 47 — Cache Abstraction Architecture (B13.6)

**Document:** `docs/47_CACHE_ARCHITECTURE.md`  
**Milestone:** B13.6 — Cache Abstraction  
**Components:** `app/cache/`, `app/adapters/strategy.py`, `app/dependencies/container.py`

---

## 1. Executive Summary

Milestone **B13.6** introduces a modular, backend-agnostic cache abstraction layer for WeatherGPT. It enables high-speed in-memory memoization (and future Redis integration) for safe, read-heavy operations while isolating the application against cache backend failures and preventing stale weather contamination.

```text
HTTP Request / Brain Tool Call
             │
             ▼
      Cache Key Builder
  (4-decimal coord normalization)
             │
             ▼
     ┌───────────────┐
     │ Cache Service │  <-- Fault-tolerant: errors are caught & logged; misses pass through
     └───────┬───────┘
      Hit /   \ Miss
     ┌───┘     └───┐
     ▼             ▼
Return Cached   Provider Cascade (Open-Meteo -> Fallbacks)
Payload         On Success: populate cache with bounded TTL
```

---

## 2. Architecture & Interfaces

### 2.1 Backend Protocol (`app/cache/base.py`)
```python
class CacheBackend(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]: ...
    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None: ...
    @abstractmethod
    async def delete(self, key: str) -> bool: ...
    @abstractmethod
    async def exists(self, key: str) -> bool: ...
    @abstractmethod
    async def clear(self) -> None: ...
```

### 2.2 In-Memory Backend (`app/cache/memory.py`)
* `InMemoryCacheBackend`: Thread-safe, `asyncio.Lock`-guarded in-memory store with monotonic clock (`time.perf_counter()`) TTL validation.
* Automatically evicts expired items on read/set and enforces a maximum entries guard (`max_entries=10000`).

### 2.3 Resilient Cache Service (`app/cache/service.py`)
* Wraps the backend with fail-safe error isolation: cache backend timeouts or disconnects return `None` (cache miss) or log warnings on write, guaranteeing that **cache failures never crash an API endpoint or brain execution**.

---

## 3. Deterministic Key Generation & Normalization

Defined in `app/cache/keys.py`:

| Operation | Cache Key Template | Canonical Normalization |
| :--- | :--- | :--- |
| **Current Weather** | `weather:current:{lat}:{lon}` | Lat/Lon rounded to 4 decimals (~11m resolution) |
| **Forecast** | `weather:forecast:{lat}:{lon}:{days}` | Lat/Lon 4 decimals, integer days |
| **Alerts** | `weather:alerts:{lat}:{lon}` | Lat/Lon 4 decimals |
| **GIS Boundary** | `gis:boundary:{level}:{code}` | Level & Code uppercase (`gis:boundary:STATE:IN-MH`) |
| **NWP Grid** | `nwp:grid:{model}:{lat}:{lon}` | Lowercase model, Lat/Lon 4 decimals |

**Security Guarantee:** Zero user identifiers, session tokens, or API credentials appear in cache keys.

---

## 4. Bounded TTL Strategy

| Domain | TTL Duration | Rationale |
| :--- | :--- | :--- |
| **Current Weather** | `300.0s` (5 min) | Fast updates while absorbing high-frequency burst traffic |
| **Weather Forecast**| `1800.0s` (30 min) | Model run updates occur at multi-hour intervals |
| **Official Alerts** | `180.0s` (3 min) | Fast turnaround for urgent IMD OASIS CAP warnings |
| **GIS Boundaries** | `86400.0s` (24 hr) | Administrative borders are static geographical fixtures |
| **NWP Grid** | `3600.0s` (1 hr) | Atmospheric prognostics match GFS 0.25° run intervals |

---

## 5. Cache Safety & Non-Caching Rules

* **Errors & Failures:** 4xx/5xx HTTP errors, `ProviderUnavailableError`, `AdapterError`, and circuit breaker trips are **never cached**, ensuring immediate retries on subsequent requests.
* **Non-Idempotent / Mutations:** Chat turns with conversational context updates and user state changes bypass the cache.

---

## 6. Verification & Test Evidence

* CRUD operations, TTL expiration, max capacity eviction, coordinate normalization: `tests/test_cache_abstraction.py` (7/7 passed).
* Fallback cascade integration and error isolation verified.
* Full test regression suite: 511 passed, 21 skipped.

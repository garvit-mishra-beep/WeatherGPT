# 48 — In-Flight Request Deduplication Architecture (B13.7)

**Document:** `docs/48_REQUEST_DEDUPLICATION.md`  
**Milestone:** B13.7 — Request Deduplication  
**Components:** `app/cache/deduplicator.py`, `app/adapters/strategy.py`, `app/dependencies/container.py`, `app/api/v1/system.py`

---

## 1. Executive Summary

Milestone **B13.7** adds an asynchronous in-flight request coalescing and deduplication engine (`RequestDeduplicator`). When dozens or hundreds of concurrent identical requests arrive simultaneously before cache population, they are coalesced into a single in-flight asynchronous execution rather than flooding external meteorological data providers or the PostgreSQL/PostGIS database.

```text
100 Concurrent Identical Requests
                │
                ▼
      ┌────────────────────┐
      │  Cache Miss Check  │
      └─────────┬──────────┘
                │
                ▼
     ┌──────────────────────┐
     │ Request Deduplicator │  <-- First request spawns Task; 99 join the in-flight Task
     └──────────┬───────────┘
                │ (1 In-flight Task)
                ▼
    Weather Provider Manager
                │
                ▼
        External Provider (Open-Meteo / Fallbacks)
                │
                ▼ (1 Response)
    ┌───────────────────────┐
    │ Populate Cache (TTL)  │
    └───────────┬───────────┘
                │
   All 100 Callers Receive Valid Result
```

---

## 2. In-Flight Task Registry & Coalescing

### 2.1 Concurrency Architecture (`app/cache/deduplicator.py`)
```python
class RequestDeduplicator:
    def __init__(self, metrics: Optional[DeduplicationMetrics] = None) -> None:
        self._in_flight: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self.metrics = metrics or DeduplicationMetrics()

    async def execute(self, key: str, factory: Callable[[], Awaitable[T]], operation: str) -> T:
        async with self._lock:
            if key in self._in_flight:
                task = self._in_flight[key]
                self.metrics.record_hit(operation)
            else:
                self.metrics.record_operation(operation)
                task = asyncio.create_task(self._run_and_clean(key, factory, operation))
                self._in_flight[key] = task

        return await asyncio.shield(task)
```

### 2.2 Caller Cancellation Safety
Using `asyncio.shield(task)` guarantees that if one HTTP client disconnects or cancels its individual coroutine, the underlying shared provider fetch task continues executing to completion for all other concurrent callers.

### 2.3 Automatic Registry Cleanup
In `_run_and_clean`, a `finally` block removes `self._in_flight.pop(key, None)` immediately upon success, exception, or timeout. This guarantees **zero memory leaks and unbounded growth protection**.

---

## 3. Shared Failure & Retry Behavior

* If the single shared operation encounters an error (e.g. `ProviderUnavailableError` or timeout), the exception is propagated to all waiting callers.
* The in-flight registry is cleaned up immediately, ensuring that subsequent requests can launch fresh retry attempts without being permanently blocked.

---

## 4. Telemetry & Deduplication Metrics

The `DeduplicationMetrics` registry records:
* **`weathergpt_deduplication_operations_total`**: `operation -> int` (number of unique underlying tasks launched)
* **`weathergpt_deduplication_hits_total`**: `operation -> int` (number of concurrent callers coalesced into existing tasks)
* **`weathergpt_deduplication_failures_total`**: `operation -> int`

Exposed at `GET /api/v1/metrics`:
```json
{
  "deduplication": {
    "weathergpt_deduplication_operations_total": [
      {"operation": "current_weather", "count": 1}
    ],
    "weathergpt_deduplication_hits_total": [
      {"operation": "current_weather", "count": 9}
    ],
    "weathergpt_deduplication_failures_total": [],
    "totals": {
      "operations": 1,
      "hits": 9,
      "failures": 0
    }
  }
}
```

---

## 5. Verification & Test Evidence

* Single task launch, 10 concurrent requests coalescing (1 provider call, 9 hits), independent key isolation: `tests/test_request_deduplication.py` (7/7 passed).
* Shared failure propagation, cancellation shielding, memory cleanup verified.
* Full backend test suite regression: 518 passed, 21 skipped.
* Android unit tests: 105 passed.

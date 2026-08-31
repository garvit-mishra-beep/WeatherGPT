"""In-flight asynchronous request coalescing and deduplication.

Prevents duplicate expensive upstream provider/database calls when identical
concurrent requests arrive simultaneously.
"""

import asyncio
from collections import defaultdict
import logging
import threading
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DeduplicationMetrics:
    """Telemetry registry for in-flight request coalescing."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with getattr(self, "_lock", threading.Lock()):
            self.operations_total: Dict[str, int] = defaultdict(int)
            self.hits_total: Dict[str, int] = defaultdict(int)
            self.failures_total: Dict[str, int] = defaultdict(int)

    def record_operation(self, operation: str) -> None:
        with self._lock:
            self.operations_total[operation] += 1

    def record_hit(self, operation: str) -> None:
        with self._lock:
            self.hits_total[operation] += 1

    def record_failure(self, operation: str) -> None:
        with self._lock:
            self.failures_total[operation] += 1

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "weathergpt_deduplication_operations_total": [
                    {"operation": k, "count": v} for k, v in sorted(self.operations_total.items())
                ],
                "weathergpt_deduplication_hits_total": [
                    {"operation": k, "count": v} for k, v in sorted(self.hits_total.items())
                ],
                "weathergpt_deduplication_failures_total": [
                    {"operation": k, "count": v} for k, v in sorted(self.failures_total.items())
                ],
                "totals": {
                    "operations": sum(self.operations_total.values()),
                    "hits": sum(self.hits_total.values()),
                    "failures": sum(self.failures_total.values()),
                },
            }


class RequestDeduplicator:
    """Coalesces identical concurrent async operations to execute only once."""

    def __init__(self, metrics: Optional[DeduplicationMetrics] = None) -> None:
        self._in_flight: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self.metrics = metrics or DeduplicationMetrics()

    async def execute(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
        operation: str = "generic",
    ) -> T:
        """Execute or join an in-flight asynchronous operation identified by key.

        - If no operation is in flight for key, launches a new shielded Task.
        - If an identical operation is already in flight, awaits the existing Task without re-running factory.
        - Guarantees proper cleanup from in-flight registry on success, exception, or cancellation.
        - Individual caller cancellation does not abort the underlying task if other callers depend on it.
        """
        async with self._lock:
            if key in self._in_flight:
                task = self._in_flight[key]
                self.metrics.record_hit(operation)
            else:
                self.metrics.record_operation(operation)
                task = asyncio.create_task(self._run_and_clean(key, factory, operation))
                self._in_flight[key] = task

        # Await shielded task so one caller's cancellation does not cancel the shared task
        return await asyncio.shield(task)

    async def _run_and_clean(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
        operation: str,
    ) -> T:
        try:
            result = await factory()
            return result
        except Exception:
            self.metrics.record_failure(operation)
            raise
        finally:
            async with self._lock:
                self._in_flight.pop(key, None)

    @property
    def in_flight_count(self) -> int:
        return len(self._in_flight)


# Process-wide singleton
default_deduplicator = RequestDeduplicator()

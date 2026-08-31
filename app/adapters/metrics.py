"""WeatherGPT Provider Observability & Metrics Registry.

Tracks provider request volumes, latency distributions, failure taxonomies,
retries, circuit breaker state changes, and fallback cascades.
Adheres strictly to low-cardinality label rules (provider, operation, status/category).
"""

from collections import defaultdict
from contextlib import asynccontextmanager
import logging
import threading
import time
from typing import Any, AsyncGenerator, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ProviderMetricsRegistry:
    """In-memory metrics accumulator for upstream meteorological and air-quality providers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        """Reset all metrics counters and latency summaries."""
        with getattr(self, "_lock", threading.Lock()):
            # Counters: Dict[Tuple[str, ...], int]
            self.requests_total: Dict[Tuple[str, str], int] = defaultdict(int)
            self.success_total: Dict[Tuple[str, str], int] = defaultdict(int)
            self.failures_total: Dict[Tuple[str, str, str], int] = defaultdict(int)
            self.timeouts_total: Dict[Tuple[str, str], int] = defaultdict(int)
            self.retries_total: Dict[Tuple[str, str], int] = defaultdict(int)
            self.rate_limits_total: Dict[Tuple[str, str], int] = defaultdict(int)
            self.circuit_open_total: Dict[str, int] = defaultdict(int)
            self.circuit_recovery_total: Dict[str, int] = defaultdict(int)
            self.fallback_total: Dict[Tuple[str, str, str], int] = defaultdict(int)

            # Latencies: Dict[Tuple[str, str, str], Dict[str, float]]
            self.latencies: Dict[Tuple[str, str, str], Dict[str, float]] = defaultdict(
                lambda: {"count": 0.0, "total_seconds": 0.0, "min_seconds": float("inf"), "max_seconds": 0.0, "last_seconds": 0.0}
            )

    def record_request(self, provider: str, operation: str) -> None:
        with self._lock:
            self.requests_total[(provider, operation)] += 1

    def record_success(self, provider: str, operation: str, duration_seconds: float) -> None:
        with self._lock:
            self.success_total[(provider, operation)] += 1
            lat = self.latencies[(provider, operation, "success")]
            lat["count"] += 1
            lat["total_seconds"] += duration_seconds
            lat["min_seconds"] = min(lat["min_seconds"], duration_seconds)
            lat["max_seconds"] = max(lat["max_seconds"], duration_seconds)
            lat["last_seconds"] = duration_seconds

    def record_failure(
        self,
        provider: str,
        operation: str,
        error_category: str,
        duration_seconds: float,
    ) -> None:
        with self._lock:
            self.failures_total[(provider, operation, error_category)] += 1
            lat = self.latencies[(provider, operation, "failure")]
            lat["count"] += 1
            lat["total_seconds"] += duration_seconds
            lat["min_seconds"] = min(lat["min_seconds"], duration_seconds)
            lat["max_seconds"] = max(lat["max_seconds"], duration_seconds)
            lat["last_seconds"] = duration_seconds

    def record_timeout(self, provider: str, operation: str) -> None:
        with self._lock:
            self.timeouts_total[(provider, operation)] += 1

    def record_retry(self, provider: str, operation: str) -> None:
        with self._lock:
            self.retries_total[(provider, operation)] += 1

    def record_rate_limit(self, provider: str, operation: str) -> None:
        with self._lock:
            self.rate_limits_total[(provider, operation)] += 1

    def record_circuit_open(self, provider: str) -> None:
        with self._lock:
            self.circuit_open_total[provider] += 1

    def record_circuit_recovery(self, provider: str) -> None:
        with self._lock:
            self.circuit_recovery_total[provider] += 1

    def record_fallback(self, from_provider: str, to_provider: str, operation: str) -> None:
        with self._lock:
            self.fallback_total[(from_provider, to_provider, operation)] += 1

    @asynccontextmanager
    async def measure(
        self, provider: str, operation: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Async context manager to automatically measure latency and track outcomes."""
        self.record_request(provider, operation)
        start_time = time.perf_counter()
        context: Dict[str, Any] = {"status": "in_flight"}
        try:
            yield context
            duration = time.perf_counter() - start_time
            self.record_success(provider, operation, duration)
            context["status"] = "success"
            context["duration_seconds"] = duration
        except Exception as e:
            duration = time.perf_counter() - start_time
            error_cat = getattr(e, "code", type(e).__name__)
            self.record_failure(provider, operation, error_cat, duration)
            context["status"] = "failure"
            context["error_category"] = error_cat
            context["duration_seconds"] = duration
            raise

    def get_summary(self) -> Dict[str, Any]:
        """Returns structured JSON summary of provider metrics."""
        with self._lock:
            requests = [
                {"provider": k[0], "operation": k[1], "count": v}
                for k, v in sorted(self.requests_total.items())
            ]
            successes = [
                {"provider": k[0], "operation": k[1], "count": v}
                for k, v in sorted(self.success_total.items())
            ]
            failures = [
                {"provider": k[0], "operation": k[1], "error_category": k[2], "count": v}
                for k, v in sorted(self.failures_total.items())
            ]
            timeouts = [
                {"provider": k[0], "operation": k[1], "count": v}
                for k, v in sorted(self.timeouts_total.items())
            ]
            retries = [
                {"provider": k[0], "operation": k[1], "count": v}
                for k, v in sorted(self.retries_total.items())
            ]
            rate_limits = [
                {"provider": k[0], "operation": k[1], "count": v}
                for k, v in sorted(self.rate_limits_total.items())
            ]
            circuit_opens = [
                {"provider": k, "count": v}
                for k, v in sorted(self.circuit_open_total.items())
            ]
            circuit_recoveries = [
                {"provider": k, "count": v}
                for k, v in sorted(self.circuit_recovery_total.items())
            ]
            fallbacks = [
                {"from_provider": k[0], "to_provider": k[1], "operation": k[2], "count": v}
                for k, v in sorted(self.fallback_total.items())
            ]
            latency_summary = []
            for (provider, operation, status), lat in sorted(self.latencies.items()):
                count = lat["count"]
                avg_sec = lat["total_seconds"] / count if count > 0 else 0.0
                min_sec = lat["min_seconds"] if count > 0 else 0.0
                latency_summary.append({
                    "provider": provider,
                    "operation": operation,
                    "status": status,
                    "count": int(count),
                    "avg_ms": round(avg_sec * 1000, 2),
                    "min_ms": round(min_sec * 1000, 2),
                    "max_ms": round(lat["max_seconds"] * 1000, 2),
                    "last_ms": round(lat["last_seconds"] * 1000, 2),
                })

            return {
                "weathergpt_provider_requests_total": requests,
                "weathergpt_provider_success_total": successes,
                "weathergpt_provider_failures_total": failures,
                "weathergpt_provider_timeouts_total": timeouts,
                "weathergpt_provider_retries_total": retries,
                "weathergpt_provider_rate_limits_total": rate_limits,
                "weathergpt_provider_circuit_open_total": circuit_opens,
                "weathergpt_provider_circuit_recovery_total": circuit_recoveries,
                "weathergpt_provider_fallback_total": fallbacks,
                "weathergpt_provider_latencies": latency_summary,
            }


# Global singleton instance
provider_metrics = ProviderMetricsRegistry()

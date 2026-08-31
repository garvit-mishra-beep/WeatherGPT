"""LLM Inference Telemetry and Metrics Registry."""

from collections import defaultdict
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class LLMMetricsRegistry:
    """In-memory metrics registry for LLM inference requests and latencies."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        """Reset all LLM metric counters."""
        with getattr(self, "_lock", threading.Lock()):
            self.requests_total: Dict[str, int] = defaultdict(int)  # model -> count
            self.failures_total: Dict[Tuple[str, str], int] = defaultdict(int)  # (model, error_type) -> count
            self.retries_total: Dict[str, int] = defaultdict(int)  # model -> count
            self.latencies: Dict[str, Dict[str, float]] = defaultdict(
                lambda: {
                    "count": 0.0,
                    "total_seconds": 0.0,
                    "min_seconds": float("inf"),
                    "max_seconds": 0.0,
                    "last_seconds": 0.0,
                }
            )

    def record_request(self, model: str) -> None:
        with self._lock:
            self.requests_total[model] += 1

    def record_retry(self, model: str) -> None:
        with self._lock:
            self.retries_total[model] += 1

    def record_failure(self, model: str, error_type: str) -> None:
        with self._lock:
            self.failures_total[(model, error_type)] += 1

    def record_latency(self, model: str, duration_seconds: float) -> None:
        with self._lock:
            lat = self.latencies[model]
            lat["count"] += 1
            lat["total_seconds"] += duration_seconds
            lat["min_seconds"] = min(lat["min_seconds"], duration_seconds)
            lat["max_seconds"] = max(lat["max_seconds"], duration_seconds)
            lat["last_seconds"] = duration_seconds

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            requests = [{"model": m, "count": c} for m, c in sorted(self.requests_total.items())]
            failures = [
                {"model": m, "error_type": et, "count": c}
                for (m, et), c in sorted(self.failures_total.items())
            ]
            retries = [{"model": m, "count": c} for m, c in sorted(self.retries_total.items())]
            latency_summary = []
            for model, lat in sorted(self.latencies.items()):
                count = lat["count"]
                avg_sec = lat["total_seconds"] / count if count > 0 else 0.0
                min_sec = lat["min_seconds"] if count > 0 and lat["min_seconds"] != float("inf") else 0.0
                latency_summary.append({
                    "model": model,
                    "count": int(count),
                    "avg_ms": round(avg_sec * 1000, 2),
                    "min_ms": round(min_sec * 1000, 2),
                    "max_ms": round(lat["max_seconds"] * 1000, 2),
                    "last_ms": round(lat["last_seconds"] * 1000, 2),
                })

            return {
                "weathergpt_llm_requests_total": requests,
                "weathergpt_llm_failures_total": failures,
                "weathergpt_llm_retries_total": retries,
                "weathergpt_llm_duration_seconds": latency_summary,
                "totals": {
                    "requests": sum(self.requests_total.values()),
                    "failures": sum(self.failures_total.values()),
                    "retries": sum(self.retries_total.values()),
                },
            }


default_llm_metrics = LLMMetricsRegistry()

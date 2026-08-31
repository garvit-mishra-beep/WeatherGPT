"""Deterministic Tool Execution Telemetry and Metrics Registry."""

from collections import defaultdict
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ToolMetricsRegistry:
    """In-memory metrics registry for deterministic Tool Gateway executions."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        """Reset all tool metric counters."""
        with getattr(self, "_lock", threading.Lock()):
            self.executions_total: Dict[str, int] = defaultdict(int)  # tool_name -> count
            self.failures_total: Dict[Tuple[str, str], int] = defaultdict(int)  # (tool_name, error_type) -> count
            self.latencies: Dict[str, Dict[str, float]] = defaultdict(
                lambda: {
                    "count": 0.0,
                    "total_seconds": 0.0,
                    "min_seconds": float("inf"),
                    "max_seconds": 0.0,
                    "last_seconds": 0.0,
                }
            )

    def record_execution(self, tool_name: str) -> None:
        with self._lock:
            self.executions_total[tool_name] += 1

    def record_failure(self, tool_name: str, error_type: str) -> None:
        with self._lock:
            self.failures_total[(tool_name, error_type)] += 1

    def record_latency(self, tool_name: str, duration_seconds: float) -> None:
        with self._lock:
            lat = self.latencies[tool_name]
            lat["count"] += 1
            lat["total_seconds"] += duration_seconds
            lat["min_seconds"] = min(lat["min_seconds"], duration_seconds)
            lat["max_seconds"] = max(lat["max_seconds"], duration_seconds)
            lat["last_seconds"] = duration_seconds

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            executions = [{"tool": t, "count": c} for t, c in sorted(self.executions_total.items())]
            failures = [
                {"tool": t, "error_type": et, "count": c}
                for (t, et), c in sorted(self.failures_total.items())
            ]
            latency_summary = []
            for tool, lat in sorted(self.latencies.items()):
                count = lat["count"]
                avg_sec = lat["total_seconds"] / count if count > 0 else 0.0
                min_sec = lat["min_seconds"] if count > 0 and lat["min_seconds"] != float("inf") else 0.0
                latency_summary.append({
                    "tool": tool,
                    "count": int(count),
                    "avg_ms": round(avg_sec * 1000, 2),
                    "min_ms": round(min_sec * 1000, 2),
                    "max_ms": round(lat["max_seconds"] * 1000, 2),
                    "last_ms": round(lat["last_seconds"] * 1000, 2),
                })

            return {
                "weathergpt_tool_executions_total": executions,
                "weathergpt_tool_failures_total": failures,
                "weathergpt_tool_duration_seconds": latency_summary,
                "totals": {
                    "executions": sum(self.executions_total.values()),
                    "failures": sum(self.failures_total.values()),
                },
            }


default_tool_metrics = ToolMetricsRegistry()

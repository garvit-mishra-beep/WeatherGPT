"""WeatherGPT HTTP/API Observability & Metrics Registry.

Tracks application-level HTTP request volumes, response statuses, error rates
(4xx/5xx), and monotonic latency distributions adhering strictly to low-cardinality
labels (HTTP method, normalized route template, status code / error class).
"""

from collections import defaultdict
import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple
from starlette.requests import Request

logger = logging.getLogger(__name__)


def normalize_route(request: Request) -> str:
    """Extract low-cardinality normalized route template from request scope.

    Uses FastAPI/Starlette route metadata (e.g. '/api/v1/gis/boundary/{level}/{code}')
    rather than high-cardinality path strings containing user IDs or coordinate pairs.
    """
    route = request.scope.get("route")
    if route and hasattr(route, "path"):
        return str(route.path)
    # If route was not matched (e.g., 404), return a static low-cardinality placeholder
    path = request.url.path
    if path.startswith("/api/v1/"):
        return "/api/v1/*"
    return "unmatched"


class APIMetricsRegistry:
    """In-memory metrics registry for WeatherGPT HTTP/API traffic."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        """Reset all metrics counters and latency summaries."""
        with getattr(self, "_lock", threading.Lock()):
            # Counters:
            # (method, route) -> count
            self.requests_total: Dict[Tuple[str, str], int] = defaultdict(int)
            # (method, route, status_code) -> count
            self.responses_total: Dict[Tuple[str, str, int], int] = defaultdict(int)
            # (method, route) -> count
            self.success_total: Dict[Tuple[str, str], int] = defaultdict(int)
            # (method, route, error_class) -> count (e.g. 4xx, 5xx)
            self.errors_total: Dict[Tuple[str, str, str], int] = defaultdict(int)

            # Latency summary: (method, route) -> stats
            self.latencies: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(
                lambda: {
                    "count": 0.0,
                    "total_seconds": 0.0,
                    "min_seconds": float("inf"),
                    "max_seconds": 0.0,
                    "last_seconds": 0.0,
                }
            )

    def record_request(self, method: str, route: str) -> None:
        with self._lock:
            self.requests_total[(method, route)] += 1

    def record_response(
        self,
        method: str,
        route: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        with self._lock:
            self.responses_total[(method, route, status_code)] += 1

            if 200 <= status_code < 400:
                self.success_total[(method, route)] += 1
            elif 400 <= status_code < 500:
                self.errors_total[(method, route, "4xx")] += 1
            elif status_code >= 500:
                self.errors_total[(method, route, "5xx")] += 1

            lat = self.latencies[(method, route)]
            lat["count"] += 1
            lat["total_seconds"] += duration_seconds
            lat["min_seconds"] = min(lat["min_seconds"], duration_seconds)
            lat["max_seconds"] = max(lat["max_seconds"], duration_seconds)
            lat["last_seconds"] = duration_seconds

    def get_summary(self) -> Dict[str, Any]:
        """Returns structured JSON summary of API metrics."""
        with self._lock:
            requests = [
                {"method": k[0], "route": k[1], "count": v}
                for k, v in sorted(self.requests_total.items())
            ]
            responses = [
                {"method": k[0], "route": k[1], "status_code": k[2], "count": v}
                for k, v in sorted(self.responses_total.items())
            ]
            successes = [
                {"method": k[0], "route": k[1], "count": v}
                for k, v in sorted(self.success_total.items())
            ]
            errors = [
                {"method": k[0], "route": k[1], "error_class": k[2], "count": v}
                for k, v in sorted(self.errors_total.items())
            ]
            latency_summary = []
            for (method, route), lat in sorted(self.latencies.items()):
                count = lat["count"]
                avg_sec = lat["total_seconds"] / count if count > 0 else 0.0
                min_sec = lat["min_seconds"] if count > 0 and lat["min_seconds"] != float("inf") else 0.0
                latency_summary.append({
                    "method": method,
                    "route": route,
                    "count": int(count),
                    "avg_ms": round(avg_sec * 1000, 2),
                    "min_ms": round(min_sec * 1000, 2),
                    "max_ms": round(lat["max_seconds"] * 1000, 2),
                    "last_ms": round(lat["last_seconds"] * 1000, 2),
                })

            total_reqs = sum(self.requests_total.values())
            total_succ = sum(self.success_total.values())
            total_4xx = sum(v for k, v in self.errors_total.items() if k[2] == "4xx")
            total_5xx = sum(v for k, v in self.errors_total.items() if k[2] == "5xx")

            return {
                "weathergpt_http_requests_total": requests,
                "weathergpt_http_responses_total": responses,
                "weathergpt_http_success_total": successes,
                "weathergpt_http_errors_total": errors,
                "weathergpt_http_request_duration_seconds": latency_summary,
                "totals": {
                    "requests": total_reqs,
                    "success": total_succ,
                    "errors_4xx": total_4xx,
                    "errors_5xx": total_5xx,
                },
            }


# Process-wide singleton
api_metrics = APIMetricsRegistry()

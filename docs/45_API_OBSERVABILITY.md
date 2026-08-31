# 45 — API Observability & Request Metrics (B13.4)

**Document:** `docs/45_API_OBSERVABILITY.md`  
**Milestone:** B13.4 — Request/API Metrics  
**Component:** `app/core/metrics.py`, `app/core/middleware.py`, `app/api/v1/system.py`

---

## 1. Executive Summary

Milestone **B13.4** establishes application-level HTTP/API observability for the WeatherGPT backend. While B13.3 instruments upstream external meteorological data providers, B13.4 provides full visibility into incoming HTTP traffic originating from client interfaces (mobile Android app, web, API consumers).

```text
Android / Client
       │
       ▼
   FastAPI
       │
┌──────────────────────────────┐
│  REQUEST METRICS (B13.4)     │  <-- Monotonic latency, low-cardinality route normalization, status codes
└──────────────┬───────────────┘
               │
               ▼
      Domain Brains / Tools
               │
               ▼
   Weather Provider Manager
               │
┌──────────────────────────────┐
│  PROVIDER METRICS (B13.3)    │  <-- Upstream provider volumes, latencies, circuit breaker states
└──────────────┬───────────────┘
               │
               ▼
      External Providers
```

---

## 2. Metrics Taxonomy & Low-Cardinality Design

To prevent metric cardinality explosions, metric labels are strictly restricted to:
1. **HTTP Method:** `GET`, `POST`, etc.
2. **Normalized Route Template:** FastAPI route path pattern (e.g. `/api/v1/gis/boundary/{level}/{code}`, `/api/v1/weather/current`) rather than raw parameter paths.
3. **Status Code & Error Class:** HTTP integer status codes (`200`, `400`, `404`, `500`) and classes (`4xx`, `5xx`).

### Forbidden Labels (Strictly Enforced)
* `user_id` / `session_id`
* `request_id`
* Geographic coordinates (`lat`, `lon`, bounding boxes)
* Full query strings
* Unsanitized dynamic error messages

---

## 3. Implemented Telemetry Counters & Latencies

The `APIMetricsRegistry` (`app/core/metrics.py`) tracks:

* **`weathergpt_http_requests_total`**: `(method, normalized_route) -> int`
* **`weathergpt_http_responses_total`**: `(method, normalized_route, status_code) -> int`
* **`weathergpt_http_success_total`**: `(method, normalized_route) -> int` (2xx/3xx)
* **`weathergpt_http_errors_total`**: `(method, normalized_route, error_class) -> int` (4xx, 5xx)
* **`weathergpt_http_request_duration_seconds`**: Monotonic clock (`time.perf_counter()`) calculating `avg_ms`, `min_ms`, `max_ms`, `last_ms`, and `count`.
* **Summary Totals**: High-level counts of total requests, successful requests, 4xx errors, and 5xx errors.

---

## 4. Endpoints & Integration

### 4.1 Middleware Pipeline
`APIMetricsMiddleware` is registered in `create_app` (`app/core/factory.py`) alongside `RequestIDMiddleware` and `RequestContextLoggingMiddleware`.

### 4.2 System Telemetry Endpoint
`GET /api/v1/metrics` exposes application-level API metrics and upstream provider metrics in a unified JSON payload:

```json
{
  "api": {
    "weathergpt_http_requests_total": [
      {"method": "GET", "route": "/api/v1/weather/current", "count": 42}
    ],
    "weathergpt_http_responses_total": [
      {"method": "GET", "route": "/api/v1/weather/current", "status_code": 200, "count": 42}
    ],
    "weathergpt_http_request_duration_seconds": [
      {
        "method": "GET",
        "route": "/api/v1/weather/current",
        "count": 42,
        "avg_ms": 3.45,
        "min_ms": 1.21,
        "max_ms": 12.04,
        "last_ms": 2.89
      }
    ],
    "totals": {
      "requests": 42,
      "success": 42,
      "errors_4xx": 0,
      "errors_5xx": 0
    }
  },
  "providers": {
    "weathergpt_provider_requests_total": [...],
    "weathergpt_provider_latencies": [...]
  },
  "timestamp": "2026-08-31T11:05:00.000000Z"
}
```

---

## 5. Verification & Test Evidence

* Unit counters, error classes, status code tracking: `tests/test_api_metrics.py` (4/4 passed).
* Route template normalization verified without leaking dynamic paths (`/api/v1/gis/boundary/{level}/{code}`).
* Zero credential leakage in metrics summaries.
* Full backend test suite regression: 497 passed, 21 skipped.

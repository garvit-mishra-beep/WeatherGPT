# 50 — API Rate Limiting & Abuse Protection (B13.9)

**Document:** `docs/50_API_RATE_LIMITING.md`  
**Milestone:** B13.9 — API Rate Limiting & Abuse Protection  
**Components:** `app/core/rate_limit.py`, `app/core/factory.py`, `app/config.py`

---

## 1. Executive Summary

Milestone **B13.9** adds granular application-level sliding-window rate limiting and abuse protection:
* Granular endpoint limits:
  - `/api/v1/chat*`: 20 req/min
  - `/api/v1/nwp/*`: 30 req/min
  - `/api/v1/weather/*`: 60 req/min
  - `/api/v1/gis/*`: 60 req/min
  - Default: 60 req/min
* Unthrottled health and readiness probes (`/api/v1/health`, `/api/v1/ready`).
* Standard HTTP 429 status with `Retry-After: <seconds>` header.
* RFC 7807 problem details error payload (`RATE_LIMIT_EXCEEDED`, `retryable: true`).
* In-memory thread-safe sliding window with monotonic clock expiration.

---

## 2. Multi-Worker Architecture Note

> [!NOTE]
> `RateLimitMiddleware` operates in-memory per Uvicorn worker process. In multi-worker native Linux deployments (4 Uvicorn workers behind Nginx), coarse DDoS / burst protection is handled at the network edge by Nginx (`limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s`), while this middleware enforces granular endpoint-specific budget allocations without requiring an external Redis dependency for basic operation.

---

## 3. Rate Limit Response Contract

```json
{
  "type": "https://weathergpt.in/errors/RATE_LIMIT_EXCEEDED",
  "title": "Too Many Requests",
  "status": 429,
  "detail": "Rate limit exceeded. Please retry in 12 seconds.",
  "instance": "/api/v1/chat",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "request_id": "req_01j7abc...",
  "retryable": true,
  "retry_after_seconds": 12
}
```

---

## 4. Verification & Test Evidence

* `tests/test_api_rate_limiting.py`: 5/5 tests passed (below limit, at limit, above limit, retry-after calculation, independent client IPs, health exemptions, and concurrency burst).

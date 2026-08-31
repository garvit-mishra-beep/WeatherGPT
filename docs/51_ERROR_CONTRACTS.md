# 51 — Unified Error Contracts Architecture (B13.10)

**Document:** `docs/51_ERROR_CONTRACTS.md`  
**Milestone:** B13.10 — Unified Error Contracts  
**Components:** `app/core/exceptions.py`, `app/contracts/error.py`, `app/core/errors.py`, `app/tools/errors.py`, `app/adapters/errors.py`

---

## 1. Executive Summary

Milestone **B13.10** establishes a unified, secure, client-friendly error contract across all REST endpoints and subsystems. All HTTP errors return compliant RFC 7807 problem details with explicit machine-readable error codes and a `retryable: bool` flag to allow mobile clients (Android) to decide retry behavior deterministically.

```json
{
  "type": "https://weathergpt.in/errors/PROVIDER_UNAVAILABLE",
  "title": "Provider Unavailable",
  "status": 503,
  "detail": "Configured meteorological providers are temporarily unavailable",
  "instance": "/api/v1/weather/current",
  "error_code": "PROVIDER_UNAVAILABLE",
  "request_id": "req_01j7xyz...",
  "retryable": true,
  "timestamp": "2026-08-31T12:00:00Z"
}
```

---

## 2. HTTP Error Status Code & Subsystem Mapping

| HTTP Status | Error Code | Retryable | Description / Subsystem |
| :--- | :--- | :--- | :--- |
| **400** | `INVALID_REQUEST_ID` / `BAD_REQUEST` | `false` | Malformed request or invalid request-ID format. |
| **403** | `TOOL_SECURITY_ERROR` / `TOOL_UNAUTHORIZED` | `false` | Unauthorized tool execution or dangerous input pattern. |
| **404** | `NOT_FOUND` / `BRAIN_NOT_FOUND` | `false` | Missing resource or unregistered domain Brain. |
| **408** | `REQUEST_TIMEOUT` | `true` | Client request read timeout. |
| **409** | `CONFLICT` | `false` | Resource state conflict. |
| **422** | `VALIDATION_ERROR` / `TOOL_ARGUMENT_ERROR` / `GROUNDING_ERROR` | `false` | Pydantic validation failure, out-of-bounds coords, or ungrounded claims. |
| **429** | `RATE_LIMIT_EXCEEDED` | `true` | Exceeded endpoint rate limit quota. |
| **500** | `INTERNAL_SERVER_ERROR` / `BRAIN_EXECUTION_ERROR` / `SPATIAL_ERROR` | `false` | Unhandled internal exception. Generic safe message returned. |
| **502** | `ADAPTER_ERROR` / `ROUTER_ERROR` / `LLM_PROVIDER_ERROR` | `true` | Upstream provider, intent routing, or inference communication failure. |
| **503** | `PROVIDER_UNAVAILABLE` / `DATABASE_UNAVAILABLE` / `SERVICE_UNAVAILABLE` | `true` | Temporary dependency outage or circuit breaker trip. |
| **504** | `PROVIDER_TIMEOUT` / `LLM_TIMEOUT` / `TOOL_TIMEOUT` | `true` | Bounded execution timeout exceeded. |

---

## 3. Strict Security & Information Disclosure Constraints

1. **Zero Stack Traces in Responses:** Internal tracebacks are logged with `request_id` correlation in structured application logs but never exposed to clients.
2. **Zero SQL Fragments or Table Schemas:** Database query errors are sanitized into generic problem details.
3. **Zero Credentials / Tokens:** API keys, database connection strings, and internal authorization tokens are completely stripped.

---

## 4. Verification & Test Evidence

* `tests/test_unified_error_contracts.py`: 5/5 tests passed (422 validation, 503 provider failure with secret redaction, 504 LLM timeout, 403 tool security violation, and 500 safe unhandled crash masking).

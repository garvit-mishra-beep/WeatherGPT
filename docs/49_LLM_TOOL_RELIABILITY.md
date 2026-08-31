# 49 — LLM & Tool Execution Reliability (B13.8)

**Document:** `docs/49_LLM_TOOL_RELIABILITY.md`  
**Milestone:** B13.8 — LLM & Tool Execution Reliability  
**Components:** `app/llm/openai_compatible.py`, `app/llm/metrics.py`, `app/tools/gateway.py`, `app/tools/metrics.py`, `app/tool_calling/framework.py`

---

## 1. Executive Summary

Milestone **B13.8** implements production-grade reliability, error isolation, retry resilience, and operational observability for the LLM reasoning and deterministic Tool Gateway execution layers:
* Conservative exponential backoff retry for transient inference errors (500, 502, 503, 504, connect timeouts, connection resets).
* Immediate, non-retryable fail-fast for permanent client errors (400, 401, 403, 404, 422).
* Deterministic tool timeout containment, argument sanitization, coordinate bounding (6.0°N–38.0°N, 68.0°E–98.0°E), and polygon vertex limits.
* Protection against infinite Brain $\to$ Tool $\to$ LLM recursion with bounded round limits (`max_rounds=5`) and cumulative tool call limits (`max_total_tool_calls=10`).
* LLM and Tool metrics tracking requests, executions, failures, retries, and monotonic latency distributions.

---

## 2. Invariant & Security Guarantees

1. **The LLM is NOT the Source of Meteorological Truth:** Numerical weather values and alerts originate exclusively from verified tools.
2. **Zero Shell / Code Execution:** The LLM cannot execute arbitrary Python, invoke shell commands, access the filesystem, or query databases directly.
3. **Mandatory Tool Gateway Authorization:** Every tool invocation is strictly checked against the domain Brain's access policy.
4. **Zero Credential Exposure:** Secrets and credentials are never included in prompts, logs, tool payloads, or error responses.

---

## 3. Concurrency, Timeout & Loop Prevention

```text
Brain Request
     │
     ▼
Tool Calling Framework (max_rounds=5, max_total_tool_calls=10)
     │
     ├─► LLM Provider (bounded timeout=30s, retry transient errors x2)
     │
     └─► Tool Gateway (bounded timeout=10s, batch limit=10, bbox check)
              │
              ▼
         BaseTool Execution (isolated failures, size <= 2MB)
```

---

## 4. Telemetry Metrics

* **`weathergpt_llm_requests_total`**: `model -> int`
* **`weathergpt_llm_failures_total`**: `(model, error_type) -> int`
* **`weathergpt_llm_retries_total`**: `model -> int`
* **`weathergpt_llm_duration_seconds`**: `model -> {avg_ms, min_ms, max_ms, last_ms, count}`
* **`weathergpt_tool_executions_total`**: `tool_name -> int`
* **`weathergpt_tool_failures_total`**: `(tool_name, error_type) -> int`
* **`weathergpt_tool_duration_seconds`**: `tool_name -> {avg_ms, min_ms, max_ms, last_ms, count}`

Exposed alongside API and Provider metrics at `GET /api/v1/metrics`.

---

## 5. Verification & Test Evidence

* `tests/test_llm_tool_reliability.py`: 7/7 tests passed.

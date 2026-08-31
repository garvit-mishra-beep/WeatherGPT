# WeatherGPT Technical Specification: B13.1 + B13.2 + B13.3 Provider Resilience, Circuit Breakers & Observability

**Document:** `docs/44_PROVIDER_RESILIENCE_CIRCUIT_BREAKERS.md`  
**Milestone:** B13.1 (Provider Resilience), B13.2 (Provider Circuit Breakers), B13.3 (Provider Metrics)  
**Repository:** `WeatherGPT`  
**Scope:** Backend Hardening, Fault Isolation, Monotonic Telemetry, and Fallback Orchestration  
**Status:** COMPLETED & VERIFIED (493 backend tests, 105 Android tests passing)

---

## 1. Executive Summary

The B13.1–B13.3 hardening milestone solidifies the external integration layer of WeatherGPT against network instability, upstream provider rate limits (HTTP 429), partial infrastructure degradations, and cascading latency spikes. 

Rather than allowing external API latency or errors to propagate upward, each external provider operates behind an isolated, thread-safe and async-safe **Circuit Breaker** paired with a **Resilient HTTP Executor** and monitored via a monotonic **Provider Metrics Registry**.

```text
FastAPI Endpoints / Brains / Tool Gateway
                   │
                   ▼
       WeatherProviderManager
                   │
    ┌──────────────┴──────────────┐
    │ (Isolated Circuit Breakers) │
    ▼                             ▼
Primary Provider           Fallback Cascade
(Open-Meteo)              (OpenWeather -> WeatherAPI -> Tomorrow.io)
    │                             │
    ▼                             ▼
Resilient HTTP Executor    Resilient HTTP Executor
- Bounded Timeout          - Bounded Timeout
- Circuit Gatekeeper       - Circuit Gatekeeper
- Exponential Backoff      - Exponential Backoff
- 429 Retry-After Parser   - 429 Retry-After Parser
- Monotonic Metrics        - Monotonic Metrics
- Sensitive Secret Mask    - Sensitive Secret Mask
```

---

## 2. Core Architectural Pillars

### 2.1 B13.1 — Provider Resilience & Request Policies

Every external HTTP interaction across Open-Meteo, OpenWeather, WeatherAPI, Tomorrow.io, OpenAQ, and IMD/CAP is wrapped by `ResilientHTTPExecutor`:
1. **Bounded Timeout**: Strict timeout bounded by `PROVIDER_TIMEOUT_SECONDS` (default: 5.0s, range: 1.0s–60.0s).
2. **Transient Retry Policy**:
   - Retry Candidates: `HTTP 408`, `429`, `500`, `502`, `503`, `504`, `httpx.TimeoutException`, `httpx.ConnectError`, `httpx.NetworkError`.
   - Max Retries: `PROVIDER_MAX_RETRIES` (default: 2, range: 0–5).
   - Backoff Algorithm: Exponential backoff with random jitter $\text{delay} = \min(\text{base} \times 2^{\text{attempt}-1} + \text{jitter}, 10.0\text{s})$.
3. **Non-Retry Fast Failure**:
   - Permanent Client Errors (`HTTP 400`, `401`, `403`, `404`, `422`) immediately fast-fail without consuming retry budgets or network bandwidth.
4. **Retry-After Header Adherence**:
   - When an upstream provider returns HTTP 429 with `Retry-After`, the header value (in seconds) is parsed, bounded $[0.1, 60.0]$, and honored before subsequent retry attempts.
5. **Security & Redaction**:
   - API tokens and secrets (`key=***`, `appid=***`, `apikey=***`, `token=***`) are strictly masked in all logged URLs and exception details via `sanitize_url()`.

---

### 2.2 B13.2 — Provider Circuit Breakers

To protect the system against cascading latency failure when an upstream service is down, every provider has an independent `CircuitBreaker` instance (`app/adapters/circuit_breaker.py`):

| State | Behavior |
| :--- | :--- |
| **`CLOSED`** | Normal operation. All requests proceed. Consecutive failures increment on unhandled upstream errors. Reaching `PROVIDER_CIRCUIT_FAILURE_THRESHOLD` (default: 5) trips circuit to `OPEN`. |
| **`OPEN`** | Degraded state. `can_execute()` immediately raises `ProviderCircuitOpenError` in $<1\text{ ms}$ without making external network calls. `WeatherProviderManager` catches this immediately and routes to fallback. |
| **`HALF_OPEN`** | Cooldown probe state. After `PROVIDER_CIRCUIT_RECOVERY_SECONDS` (default: 30s), a single probe request is permitted through `asyncio.Lock` protection (`_half_open_in_flight = True`). If the probe succeeds, state reverts to `CLOSED` and failure counter resets. If the probe fails, state immediately reverts to `OPEN` with a refreshed cooldown window. |

---

### 2.3 B13.3 — Provider Metrics & Telemetry

Upstream interactions are observed through an in-memory, thread-safe `ProviderMetricsRegistry` (`app/adapters/metrics.py`) strictly using low-cardinality labels:

* `weathergpt_provider_requests_total`: `(provider, operation)`
* `weathergpt_provider_success_total`: `(provider, operation)`
* `weathergpt_provider_failures_total`: `(provider, operation, error_category)`
* `weathergpt_provider_timeouts_total`: `(provider, operation)`
* `weathergpt_provider_retries_total`: `(provider, operation)`
* `weathergpt_provider_rate_limits_total`: `(provider, operation)`
* `weathergpt_provider_circuit_open_total`: `(provider)`
* `weathergpt_provider_circuit_recovery_total`: `(provider)`
* `weathergpt_provider_fallback_total`: `(from_provider, to_provider, operation)`
* `weathergpt_provider_latencies`: `(provider, operation, status)` with min, max, avg, and last latency in milliseconds.

---

## 3. Fallback Orchestration & Non-Fatal Readiness

### 3.1 Seamless Multi-Provider Fallback
In `WeatherProviderManager`:
1. If the primary provider (`OpenMeteoProvider`) circuit is `OPEN`, it fast-fails in $<1\text{ ms}$.
2. `WeatherProviderManager` immediately iterates through the configured fallback chain (`OpenWeatherProvider` $\to$ `WeatherAPIProvider` $\to$ `TomorrowIOProvider`).
3. Upon fallback success, provenance metadata is updated (`authority = ProviderAuthority.FALLBACK`, `quality = ProviderQuality.PARTIAL`), and `weathergpt_provider_fallback_total` is incremented.
4. If all providers are unavailable, `ProviderUnavailableError` is raised. **No weather data is ever fabricated.**

### 3.2 Non-Fatal Application Readiness Probe
`ProviderHealthProbe` is registered on `/api/v1/ready`:
* Degraded provider circuits are reported in the probe metadata (`metadata.circuits`, `metadata.degraded_count`).
* Overall probe status remains `ok: true` so that temporary third-party API degradation does not bring down the WeatherGPT backend or fail Kubernetes/Systemd liveness/readiness probes.

---

## 4. Verification & Test Summary

| Test Area | Description | Status |
| :--- | :--- | :--- |
| **URL Secret Masking** | Validates regex redaction of `key`, `appid`, `apikey`, `token` in URL queries | PASSED |
| **Circuit State Transitions** | Validates `CLOSED` $\to$ `OPEN` on failure threshold $\to$ `HALF_OPEN` on cooldown $\to$ `CLOSED` on probe success | PASSED |
| **Circuit Half-Open Failure** | Validates probe failure immediately re-trips circuit to `OPEN` | PASSED |
| **Retry & Transient Errors** | Validates exponential backoff and eventual recovery on transient 500/502/503 | PASSED |
| **400 Fast Failure** | Validates 400 Bad Request fast-fails on first attempt with 0 retries | PASSED |
| **429 Rate Limiting** | Validates `Retry-After` header extraction and metric recording | PASSED |
| **Timeout & Circuit Trip** | Validates timeout exceptions retry and trip circuit to `OPEN` | PASSED |
| **Manager Fallback Cascade** | Validates primary circuit `OPEN` instantly cascades to OpenWeather with provenance tracking | PASSED |
| **All Providers Exhausted** | Validates clean `ProviderUnavailableError` when all circuits are open without data fabrication | PASSED |
| **Readiness Probe Integrity** | Validates `/api/v1/ready` reports degraded circuits without failing application readiness | PASSED |

Full Test Suite: **493 backend tests passed (21 skipped for database), 105 Android tests passed.**

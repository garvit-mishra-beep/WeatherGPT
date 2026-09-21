# Phase 9B — Operational Data Failure Matrix & Contingency Protocol

## 1. Executive Summary
This document defines the deterministic failure handling, fallback policies, circuit-breaker transitions, and pipeline response behaviors for all possible operational data ingestion failures in VAYUBODHAK.

---

## 2. Comprehensive Operational Failure Matrix

| Failure Mode | Trigger Condition | Source Status | Operational Fallback Behavior | Downstream Pipeline Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Official Warning Timeout** | IMD / NDMA CAP feed unreachable or timed out (> 10s) | `DEGRADED` | 1. Check approved local cache (`TTL_ALERTS` = 15m).<br>2. If cache hit, mark `DataSourceStatus.CACHED`.<br>3. If cache miss, mark `DataSourceStatus.UNAVAILABLE`.<br>**STRICT RULE**: Secondary weather providers are NEVER queried for official warnings. | Pipeline proceeds with `official_warnings = None` or cached warnings if valid. Flagged with `REVIEW_REQUIRED` if alerts are critical. Never guesses an alert. |
| **Primary Weather Timeout** | Open-Meteo endpoint unreachable or HTTP 5xx | `DEGRADED` | 1. Retry up to 3 times with exponential backoff & jitter.<br>2. On exhaustion, cascade to configured secondary fallback: OpenWeather -> WeatherAPI -> Tomorrow.io.<br>3. Tag output as `DataSourceStatus.FALLBACK` and `ProviderAuthority.FALLBACK`. | Pipeline accepts fallback evidence with `QualityState.VALID` but records `DataSourceStatus.FALLBACK` in `PipelineRun` and final `NirnayCard`. |
| **Malformed Response Payload** | Upstream provider returns non-JSON, invalid XML, or truncated bytes | `FAILED` | 1. Increment `consecutive_failures`.<br>2. Reject corrupt records (`records_rejected += 1`).<br>3. Fall back to cached previous valid response if within validity horizon.<br>4. Do NOT insert corrupt data into Evidence Foundation. | Rejection logged in `AdapterRunRecord`. Pipeline receives no invalid fields (`QualityState.INVALID` blocks calculation). |
| **Expired Official Warning** | Ingested CAP alert has `valid_to < now_utc` | `EXPIRED` / `STALE` | 1. Alert is parsed and retained for historical audit.<br>2. `QualityState` set to `STALE`.<br>3. Alert is excluded from active emergency directives. | Nirnay Engine evaluates no active official directives. The decision relies on current valid observation/forecast evidence. |
| **Multi-Provider Data Conflict** | Provider A reports 120 mm/h rainfall; Provider B reports 10 mm/h rainfall | `CONFLICT` | 1. Detect variance exceeding scientific tolerance ($\Delta > 30\%$).<br>2. Enforce evidence hierarchy (E0 > E1 > E2 > E3).<br>3. If unresolved across same-tier providers, set `QualityState.CONFLICT`.<br>4. Prohibit arbitrary averaging or collapsing to synthetic mean. | Pipeline marks stage with `QualityState.CONFLICT`. Pipeline state transitions to `REVIEW_REQUIRED`. NirnayCard alerts human operator of sensor/provider discrepancy. |
| **PostgreSQL / Redis Unavailable** | Database connection refused or Redis timeout | `DEGRADED` | 1. Fall back to in-memory transient cache (`MemoryCacheBackend`).<br>2. Generate in-memory `PipelineRun` with durability label `EPHEMERAL_FALLBACK`.<br>3. Prohibit false claims of durable persistence. | Pipeline executes deterministically in-memory. Response includes `durability_label = "EPHEMERAL_FALLBACK"`. |
| **All Weather Providers Unavailable** | Open-Meteo, OpenWeather, WeatherAPI, and Tomorrow.io all fail or circuits open | `UNAVAILABLE` | 1. Query local cache.<br>2. If cached observation is fresh (age < 6h), use with `DataSourceStatus.CACHED`.<br>3. If cache expired or missing, return `DataSourceStatus.UNAVAILABLE`. | Pipeline evaluates with available spatial/historical static evidence or transitions to `INSUFFICIENT_EVIDENCE`. NirnayCard outputs `INSUFFICIENT_DATA`. |
| **SSRF Injection Attempt** | Request URL points to unauthorized IP or non-whitelisted host | `BLOCKED` | 1. Intercept at `validate_outbound_url`.<br>2. Raise `SSRFSecurityError`.<br>3. Abort outbound request immediately before socket creation.<br>4. Log security violation. | Request fails with HTTP 400 Bad Request. Upstream pipeline is insulated from internal network scanning. |
| **XXE / Billion Laughs Attack** | Malformed CAP XML contains `<!ENTITY` or `<!DOCTYPE` bomb | `BLOCKED` | 1. Intercept before XML tree parsing.<br>2. Raise `CAPParseError`.<br>3. Abort parse operation; zero memory expansion. | Malformed payload rejected. Incident logged in `AdapterRunRecord`. |

---

## 3. Circuit Breaker State Transition Matrix

```text
    ┌──────────────┐
    │    CLOSED    │ ◄───────────────────────────┐
    └──────┬───────┘                             │
           │ 5 Consecutive Failures              │
           ▼                                     │ Canary Probe Succeeded
    ┌──────────────┐                             │
    │     OPEN     │                             │
    └──────┬───────┘                             │
           │ Recovery Timeout (30s Elapsed)      │
           ▼                                     │
    ┌──────────────┐                             │
    │  HALF_OPEN   │ ────────────────────────────┘
    └──────┬───────┘
           │ Canary Probe Failed
           ▼
     Back to OPEN (Cooldown 30s)
```

1. **`CLOSED`**: Requests proceed directly to upstream provider. Latencies and HTTP status codes recorded.
2. **`OPEN`**: All calls fail immediately without allocating sockets or blocking threads. Fallback cascade triggered immediately.
3. **`HALF_OPEN`**: A single canary trial request is sent. If successful, the circuit resets to `CLOSED`. If it fails, the circuit resets to `OPEN` for another cooling period.

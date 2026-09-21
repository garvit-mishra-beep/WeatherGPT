# 52 — Health, Readiness & Dependency Monitoring (B13.11)

**Document:** `docs/52_HEALTH_READINESS.md`  
**Milestone:** B13.11 — Health, Readiness & Dependency Monitoring  
**Components:** `app/api/v1/system.py`, `app/core/readiness.py`, `app/db/health.py`, `app/adapters/strategy.py`

---

## 1. Executive Summary

Milestone **B13.11** formally defines and decouples **Health (Liveness)** from **Readiness (Dependency Availability)** to enable production load balancers, reverse proxies (Nginx), and deployment orchestrators (Systemd) to make reliable routing decisions without cascading failures.

---

## 2. Health vs. Readiness Definitions

### 2.1 Health (`GET /api/v1/health`)
* **Purpose:** Proves the application ASGI worker process is alive and executing the Python event loop.
* **Execution:** Immediate ($< 1\text{ ms}$ response). Never executes database queries, spatial joins, LLM inference, or third-party HTTP calls.
* **Payload:**
  ```json
  {
    "status": "healthy",
    "app_name": "WeatherGPT",
    "environment": "production",
    "version": "v1",
    "timestamp": "2026-08-31T12:00:00Z"
  }
  ```

### 2.2 Readiness (`GET /api/v1/ready`)
* **Purpose:** Evaluates whether required dependencies are operational enough to safely serve user traffic.
* **Evaluation Criteria:**
  - `ApplicationProbe`: Application container built and initialized.
  - `DatabaseProbe`: PostgreSQL connection answers `SELECT 1` and PostGIS extension is loaded.
  - `ProviderHealthProbe`: External meteorological provider circuit status aggregated.
* **Resilience Principle:** An optional external provider outage (e.g. single circuit open) **does NOT fail the overall application readiness**, because multi-provider fallback cascades (OpenWeather, WeatherAPI, Tomorrow.io) and cached observations maintain service availability.
* **Payload:**
  ```json
  {
    "status": "ready",
    "ready": true,
    "dependencies": {
      "application": {
        "status": "connected",
        "latency_ms": 0.05,
        "detail": "application process ready"
      },
      "database": {
        "status": "connected",
        "latency_ms": 1.2,
        "detail": "database connected",
        "postgis": "3.4.0"
      },
      "providers": {
        "status": "connected",
        "latency_ms": 0.1,
        "detail": "all provider circuits normal"
      }
    }
  }
  ```

---

## 3. Security & Information Shielding

1. `DatabaseProbe` logs exact connection errors locally in structured application logs with `request_id`, but returns sanitized `detail="database unavailable"` in client-facing HTTP payloads.
2. Zero database passwords, connection URLs (`postgres://...`), or cluster topologies are exposed.

---

## 4. Verification & Test Evidence

* `tests/test_health_readiness.py`: 5/5 tests passed (liveness isolation, database connected, database down reporting `not_ready`, provider degradation resilience, and dynamic recovery).

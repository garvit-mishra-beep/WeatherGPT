# API v1 (`app/api/v1/`)

## 1. Purpose
Version `v1` of the WeatherGPT HTTP API, mounted by the factory at `/api/v1`.

## 2. Endpoints

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Liveness — lightweight, no external calls. |
| `GET` | `/api/v1/ready` | Readiness — pluggable dependency probes. |
| `GET` | `/api/v1/` | Root metadata / API navigation. |

## 3. Responsibilities
- `system.py` — source of the three system endpoints above.
- `router.py` — the central aggregator for every v1 router.

## 4. Health vs Readiness
- **`/health`** (liveness): process is up. Never performs LLM/weather/GIS/NWP or
  expensive work. Safe for Docker/load-balancer probes.
- **`/ready`** (readiness): whether the app can serve traffic given its
  dependencies. Uses `ReadinessChecker`; only real, existing probes are
  registered at the current phase.

## 5. Extension
Add feature routers here as phases progress and register them in `router.py`.

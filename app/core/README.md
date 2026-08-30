# Backend Core Infrastructure (`app/core/`)

## 1. Purpose
Cross-cutting, domain-agnostic plumbing for the WeatherGPT FastAPI backend: the
application factory, lifecycle, structured logging, request correlation
IDs, HTTP middleware, exception handling, and the pluggable readiness mechanism.

## 2. Responsibilities
- Construct and configure a complete `FastAPI` application deterministically.
- Manage startup/shutdown lifecycle and the application service container.
- Correlate and propagate `X-Request-ID` across request handling and logs.
- Emit structured, container-friendly, secret-safe JSON logs.
- Translate errors into a stable RFC 7807 `application/problem+json` surface.
- Run pluggable readiness probes (`/healthy` vs `/ready` separation).

## 3. Important Files
- `factory.py` — `create_app()`: the single application entry point.
- `lifespan.py` — `backend_lifespan`: startup/shutdown.
- `logging.py` — `StructuredJsonFormatter`, `configure_logging`.
- `request_id.py` — request correlation utilities + contextvar.
- `middleware.py` — `RequestIDMiddleware`, `RequestContextLoggingMiddleware`.
- `errors.py` — backend exception taxonomy (no handler imports).
- `exceptions.py` — RFC 7807 exception handlers.
- `readiness.py` — `ReadinessChecker` and pluggable `ReadinessProbe`s.

## 4. Architecture
```text
create_app()
  ├─ settings (production-safe validation)
  ├─ middleware (CORS → RequestID → AccessLog)
  ├─ exception handlers
  ├─ /api/<version>/ router
  └─ lifespan (builds AppContainer, computes readiness)
```

## 5. Dependencies
`fastapi`, `starlette`, `pydantic`/`pydantic-settings`, `app.config`,
`app.contracts.error` (RFC 7807), `app.dependencies.container`.

## 6. Extension Points
- **Readiness probes:** implement a `ReadinessProbe` and register it in the
  lifespan (`ApplicationProbe` is the only B1 default). DB/GIS/NWP/LLM probes are
  added in later phases.
- **Middleware:** add only genuinely useful middleware here; never domain logic.

## 7. Testing
Covered by `tests/test_backend_foundation.py`. Middleware/handlers are tested
through `fastapi.testclient.TestClient` with an isolated `app_env="test"` app.

## 8. Limitations
- At B1 readiness registers only the application probe (no fabricated checks).
- Production-insecure configuration is guarded at `create_app` runtime, not at
  `Settings` object construction (so unit tests may build value objects freely).

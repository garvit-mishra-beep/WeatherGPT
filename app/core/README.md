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

## 6. Extension Points & Readiness Probes
- **Application Probe:** Liveness memory check verifying process runtime state.
- **Database & PostGIS Probe (`DatabaseProbe`):** Async readiness probe verifying PostgreSQL pooled connection acquisition and PostGIS spatial extension availability.

## 7. Testing
Core infrastructure is covered by automated unit and integration tests with RFC 7807 error checks and request-ID propagation.

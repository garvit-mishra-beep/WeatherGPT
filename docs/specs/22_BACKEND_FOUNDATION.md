# WeatherGPT — Backend Foundation Specification

**Document:** `21_BACKEND_FOUNDATION.md`  
**Status:** Approved Technical Specification (B1 — Backend Foundation)  
**Primary Product Authority:** [docs/01_PRD.md](01_PRD.md)  
**Related Specs:** [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md), [04_INPUT_OUTPUT_CONTRACT.md](04_INPUT_OUTPUT_CONTRACT.md), [06_API_CONTRACT.md](06_API_CONTRACT.md), [15_ERROR_GUARDRAILS.md](15_ERROR_GUARDRAILS.md), [17_SETUP_DEPLOYMENT.md](17_SETUP_DEPLOYMENT.md), [20_PERFORMANCE.md](20_PERFORMANCE.md)

---

## 1. Scope

B1 establishes the production-oriented **FastAPI backend foundation** that future
phrase systems (B2 PostgreSQL/PostGIS, B3 boundaries, B4 GIS, B5 NWP, weather
ingest, B9 API surface, B10 Tool Gateway integration, B11 deployment) plug into.

B1 delivers:

* A deterministic FastAPI **application factory** (`create_app`).
* API **versioning** under a single `/api/v1` prefix.
* **Liveness** (`/api/v1/health`) and **readiness** (`/api/v1/ready`) endpoints.
* **Request correlation** (`X-Request-ID`) propagation/generation.
* Lightweight **middleware** (request ID, access logging/timing, CORS).
* **Structured** container-friendly logging.
* Unified **RFC 7807** error handling reusing `app/contracts/error.py`.
* **Dependency injection** boundaries reusing existing WeatherGPT classes.
* **Lifecycle** (startup/shutdown) management.
* Accurate **OpenAPI** metadata.
* Production-safe **configuration**.
* A production-oriented **Dockerfile** with a `/api/v1/health` probe.
* A comprehensive **pytest** suite.

**Out of scope (later phases):** PostgreSQL/PostGIS, GIS algorithms, NWP grid
processing, weather ingestion, analytics engines, mobile UI, voice, Kubernetes,
authentication redesign.

---

## 2. Backend Architecture

```text
Client (Mobile / Web)
        │ HTTPS
        ▼
   FastAPI (ASGI) ───────────── app/core/factory.create_app()
        │
        ├─ Middleware: RequestID → AccessLog → CORS
        ├─ Exception Handlers (RFC 7807, app/core/exceptions.py)
        ├─ Lifespan (app/core/lifespan.py)
        │
        ▼
   API Layer (app/api/v1) ────── /api/v1/health, /api/v1/ready
        │
        ▼
   Dependency Injection (app/dependencies)
        │
        ▼
   WeatherGPT Core Services  (existing modules, reused)
        ├─ LLMProvider          (app/llm — factory.get_llm_provider)
        ├─ ToolGateway          (app/tools — gateway, registry, catalog)
        ├─ BrainOrchestrator    (app/brains — 4 domain brains + registry)
        ├─ ContextManager       (app/context)
        └─ GroundingService     (app/grounding)
        │
        ▼
   Future Infrastructure
        ├─ PostgreSQL/PostGIS   (B2)   → DatabaseService
        ├─ Weather Providers    (ingest)→ WeatherService
        ├─ NWP                  (B5)   → NWPService
        └─ GIS / Analytics      (B4)   → GISService
```

The backend is a **monolithic modular** FastAPI package — consistent with
`docs/02` §20 (no microservice mesh / Kubernetes for MVP).

---

## 3. Repository Structure (B1 additions)

```text
app/
├── main.py                     # ASGI entrypoint -> create_app()
├── config.py                   # Typed, env-driven Settings (extended for B1)
├── core/                       # Cross-cutting backend infrastructure
│   ├── factory.py              # create_app() application factory
│   ├── lifespan.py             # Startup/shutdown lifecycle
│   ├── logging.py              # Structured JSON logging formatter
│   ├── middleware.py           # RequestID + access-log/timing middleware
│   ├── request_id.py           # ContextVar request correlation
│   ├── errors.py               # Backend exception taxonomy
│   ├── exceptions.py           # RFC 7807 exception handlers
│   └── readiness.py            # Pluggable readiness probes
├── api/
│   └── v1/
│       ├── router.py           # Central v1 router registration
│       └── system.py           # /health, /ready, / root
├── dependencies/
│   ├── container.py            # Composition root (AppContainer)
│   └── providers.py            # FastAPI Depends helpers
└── services/                   # Boundary for future services (empty at B1)
Dockerfile                      # Production backend image
.dockerignore
.env.example                    # Env-driven configuration template
```

---

## 4. Application Factory

`app/core/factory.py:create_app(settings=None, *, configure_logging_enabled=True)`

Responsibilities (deterministic order):

1. Resolve configuration (including validation of production-safe defaults).
2. Optionally configure structured logging.
3. Create the `FastAPI` instance with accurate OpenAPI metadata.
4. Bind `settings` onto `app.state.settings`.
5. Register middleware (`RequestID` outermost, then access log, then CORS).
6. Register RFC 7807 exception handlers.
7. Mount the versioned router under `/api/{version}`.
8. Attach the lifespan.

`app/main.py` is a thin ASGI entrypoint: `app = create_app(settings=settings)`.
No business logic lives in `main.py`.

---

## 5. Lifecycle

`app/core/lifespan.py:backend_lifespan`

* **Startup:** builds the `AppContainer` (deterministically wiring all existing
  WeatherGPT services) and registers the readiness probes. Only resources that
  actually exist are initialized — **not** PostgreSQL/PostGIS, NWP, or GIS.
* **Shutdown:** releases resources cleanly (e.g. resets in-memory session state).

The assembled services are stored on `app.state.container` and
`app.state.readiness` for dependency resolution.

---

## 6. API Structure & Versioning

The canonical base path is **`/api/v1`** (per `docs/06_API_CONTRACT.md` §1).

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Liveness (lightweight, no external calls) |
| `GET` | `/api/v1/ready` | Readiness (pluggable dependency probes) |
| `GET` | `/api/v1/` | Root metadata / navigation |

All v1 routers are registered centrally in `app/api/v1/router.py` under a single
prefix; future feature routers (chat, weather, farmer, research, gis, nwp) are
added there.

---

## 7. Configuration

`app/config.py:Settings` (Pydantic v2 + pydantic-settings), environment-driven.

New B1 settings (existing LLM/DB settings preserved):

| Variable | Default | Notes |
| :--- | :--- | :--- |
| `APP_ENV` | `development` | `development | staging | production | test` |
| `DEBUG` | `false` | |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Bind port |
| `API_VERSION` | `v1` | Active version segment |
| `LOG_LEVEL` | `INFO` | DEBUG/INFO/WARNING/ERROR/CRITICAL |
| `CORS_ORIGINS` | `['http://localhost:3000', ...]` | Comma-separated or JSON array |
| `REQUEST_TIMEOUT_SECONDS` | `30` | |

**Production safety (enforced at runtime by `create_app`, not at Settings
construction):** the backend refuses to boot when `APP_ENV=production` with (a)
the default insecure `SECRET_KEY`, or (b) a wildcard `CORS_ORIGINS="*"`. This
keeps the invariant "production must not silently run with insecure defaults"
while still allowing unit tests to construct `Settings` value objects.

---

## 8. Middleware

`app/core/middleware.py` (lightweight, no domain logic):

| Middleware | Role |
| :--- | :--- |
| `RequestIDMiddleware` | Accept/generate/validate `X-Request-ID`, bind to context, echo on response. |
| `RequestContextLoggingMiddleware` | Per-request timing + structured access log. |
| `CORSMiddleware` | Configuration-driven CORS (never wildcard + credentials). |

Middleware order (outermost → innermost): CORS → RequestID → AccessLog. This
places CORS first for preflight handling and binds the request ID before access
logging.

---

## 9. Request ID

`app/core/request_id.py`

* Header: `X-Request-ID`.
* A safe allowlist regex restricts trusted inbound IDs (`[A-Za-z0-9._-]`, ≤ 128
  chars) to prevent header/log-injection.
* Valid/inbound IDs are propagated; otherwise a `uuid4().hex` ID is generated.
* The ID is exposed to application code via `get_request_id()` (contextvar),
  attached to structured log records, and returned in the outbound response
  header.

---

## 10. Structured Logging

`app/core/logging.py`

* `StructuredJsonFormatter` emits single-line JSON to stdout (container/log-
  collector friendly).
* Captured fields: timestamp, level, logger, message, request_id, method, path,
  status, duration_ms.
* Sensitive keys (`secret`, `api_key`, `password`, `token`, `authorization`) are
  redacted; the `Authorization` header and request bodies are never logged.
* `configure_logging(settings)` is idempotent and tames uvicorn/httpx verbosity.

---

## 11. Error Handling

`app/core/errors.py` + `app/core/exceptions.py`, built on
`app/contracts/error.ProblemDetailRFC7807`.

| Case | Status | Format |
| :--- | :---: | :--- |
| Known backend/domain errors (`BackendError`) | configurable (400/404/409/503…) | RFC 7807 problem detail |
| Request validation (`RequestValidationError`) | 422 | RFC 7807 + `details.errors` |
| Starlette HTTP errors | as raised | RFC 7807 |
| Unexpected exceptions | 500 | Safe generic message (no stack traces leaked) |

Unexpected exceptions are fully logged server-side but never exposed to clients.

---

## 12. Health / Readiness

* **`GET /api/v1/health`** — liveness. Deliberately calls **no** LLM, weather,
  GIS, NWP, or expensive DB operations. Used for Docker/load-balancer probes.
* **`GET /api/v1/ready`** — readiness via the **pluggable** `ReadinessChecker`
  (`app/core/readiness.py`). Only probes whose dependencies actually exist are
  registered. At B1 only the base `ApplicationProbe` is registered; future
  phases add `DatabaseProbe` (B2), `GISProbe` (B4), `NWPProbe` (B5), weather,
  and LLM probes. No fabricated checks.

When probes are added, `/ready` will report them without polluting `/health`.

---

## 13. Dependency Injection

`app/dependencies/container.py:AppContainer` is the composition root. `build()`
deterministically constructs **existing** classes via existing factories (no fake
implementations):

| Provider | Source |
| :--- | :--- |
| `LLMProvider` | `app.llm.factory.get_llm_provider` |
| `ToolGateway` | `app.tools.gateway.ToolGateway` + default tools + `ToolResultCache` |
| `BrainOrchestrator` | `app.brains.orchestrator.BrainOrchestrator` + 4 brains |
| `ContextManager` | `app.context.manager.ContextManager` |
| `GroundingService` | `app.grounding.service.GroundingService` |

FastAPI `Depends` helpers live in `app/dependencies/providers.py`
(`get_container`, `get_settings`, `get_llm_provider_dep`, `get_tool_gateway`,
`get_brain_orchestrator`, `get_context_manager`, `get_grounding_service`).
Future `DatabaseService`, `WeatherService`, `GISService`, `NWPService` slots are
declared in `app/services/` (empty at B1).

---

## 14. OpenAPI

Configuration-driven metadata: title, description, version (`API_VERSION`),
tags. Swagger UI at `/docs`, ReDoc at `/redoc`, schema at `/openapi.json`. No
secrets are present in the OpenAPI document.

---

## 15. Docker

`Dockerfile` (production-oriented):

* Base: `python:3.12-slim`, multi-stage (builder virtualenv → minimal runtime).
* Non-root user (`weathergpt`, UID/GID 10001).
* No secrets baked in — all configuration via environment at runtime.
* Deterministic startup (`uvicorn app.main:app`).
* HEALTHCHECK uses `GET /api/v1/health` (lightweight).
* `.dockerignore` excludes secrets, caches, docs, and tests from the build.

> **Note:** The B1 local machine has the Docker CLI present but the Docker daemon
> was not running during verification, so an actual image build was **not**
> executed and no container startup is claimed for B1.

---

## 16. Security

* No hardcoded secrets; credentials come from `.env`/environment.
* Production refuses an insecure default `SECRET_KEY` and wildcard CORS.
* CORS never combines `*` with credentials.
* Safe exception messages: stack traces are internal-only.
* `DEBUG` is never enabled implicitly; environment-driven.
* Redacted sensitive logging; `Authorization`/bodies never logged.

Authentication is intentionally out of B1 scope (existing docs do not mandate a
new auth system at this phase).

---

## 17. Performance

Reuses the existing performance infrastructure (`app/performance`) — the B1
factory and container do **not** duplicate instrumentation or caching. The
ToolGateway is constructed with the existing `ToolResultCache` for deterministic
deduplication (per `docs/20_PERFORMANCE.md`). Request timing is captured by
`RequestContextLoggingMiddleware`; no parallel timing system is introduced.

---

## 18. Testing

`tests/test_backend_foundation.py` (31 tests) + all pre-existing suites remain
green (215 total). Coverage includes: application creation, factory, health,
readiness (incl. pluggability), request-ID generation/propagation/response,
validation errors, known application errors, unexpected exception safety, CORS,
configuration, OpenAPI, lifecycle, dependency injection, logging, root metadata,
and production-safe behavior.

**Isolation:** B1 tests require no PostgreSQL/PostGIS, GPU, real weather APIs,
IMD/GFS/ECMWF, or a production LLM. They run against `app_env="test"` (mock LLM
provider) and never touch network services.

---

## 19. Future PostgreSQL/PostGIS Integration (B2)

The factory/container/lifespan/readiness are already structured to accept a
`DatabaseService` plus a `DatabaseProbe`, and `Settings` already carries
`DATABASE_URL`. B2 will add the database adapter and wire it without reworking
the B1 foundation.

---

## 20. Future GIS Integration (B4)

Target layering:

```text
FastAPI → GISService → GISRepository → PostGIS
```

`app/services/` declares the `GISService` boundary; readiness supports a future
`GISProbe`. No PostGIS queries are implemented at B1.

---

## 21. Future NWP Integration (B5)

Target layering:

```text
FastAPI → NWPService → GridProcessor → GFS / ECMWF
```

`app/services/` declares the `NWPService` boundary; readiness supports a future
`NWPProbe`. No NWP processing is implemented at B1.

---

## 22. Architectural Invariants (Preserved)

1. LLM is **not** the source of meteorological truth.
2. Deterministic engines provide factual evidence.
3. Official warnings are immutable.
4. Brains use the Tool Gateway.
5. The Tool Gateway controls tools.
6. `EvidencePackage` grounds factual responses.
7. Numerical values remain invariant.
8. Multilingual output preserves factual values.
9. Domain calculations stay outside the LLM.
10. Existing performance infrastructure remains intact.

---

## 23. Verification Summary (B1)

* `python -m pytest -v tests/` → **215 passed** (184 pre-existing + 31 B1).
* Application factory creates a valid FastAPI app.
* `/api/v1/health` → 200 `{status: healthy, ...}`.
* `/api/v1/ready` → 200 `{ready: true, dependencies: {application: ...}}`.
* OpenAPI served at `/openapi.json`, `/docs`, `/redoc`.
* Request IDs generated and propagated end-to-end.
* Production-insecure config correctly refused at runtime.
* Docker image build **not verified** (daemon offline on the B1 host).

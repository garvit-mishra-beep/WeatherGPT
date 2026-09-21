# WeatherGPT — Database (PostgreSQL + PostGIS) Foundation Specification

**Document:** `22_DATABASE_POSTGIS_FOUNDATION.md`  
**Status:** Approved Technical Specification (B2 — PostgreSQL + PostGIS Foundation)  
**Primary Product Authority:** [docs/01_PRD.md](01_PRD.md)  
**Related Specs:** [09_GIS_SPEC.md](09_GIS_SPEC.md), [10_DATABASE_SCHEMA.md](10_DATABASE_SCHEMA.md), [17_SETUP_DEPLOYMENT.md](17_SETUP_DEPLOYMENT.md), [22_BACKEND_FOUNDATION.md](22_BACKEND_FOUNDATION.md)

> **Filename numbering note:** this document uses the `22_` prefix as specified by
> the B2 task instruction. The B1 specification currently lives at
> `docs/22_BACKEND_FOUNDATION.md` (whose internal header claims `21_`). Because both
> documents share the `22_` filename prefix, a renumbering is recommended in a
> later housekeeping pass.

---

## 1. Scope

B2 establishes the **PostgreSQL + PostGIS foundation** that all later data-bearing
phases (B3 India boundaries, B4 GIS, B5 NWP, weather ingest, analytics, tools)
depend upon. It provides the storage, connection, migration, and readiness wiring —
but deliberately ships **no domain tables** (no weather, crop, or boundary models).

B2 delivers:

* A **SQLAlchemy 2.x async** DeclarativeBase (`Base`) with a `TimestampMixin`.
* **PostGIS-enabled spatial column helpers** (`geometry`, `geography`) and
  convenience aliases (`MultiPolygon`, `Polygon`, `Point`, `MultiLineString`),
  centralising EPSG:4326 as the canonical storage CRS.
* A lazy, **pooled async engine** (`asyncpg`) plus an `async_sessionmaker` factory.
* A generic **repository foundation** (`BaseRepository`) that never commits implicitly.
* A **`DatabaseProbe`** readiness probe (PostgreSQL connectivity + PostGIS presence/version).
* An **Alembic** migration environment (async, environment-driven) with an initial
  migration that enables the PostgreSQL `postgis` extension.
* A **`DatabaseService`** ownership boundary wired into `AppContainer`, exposed on
  the B1 `/api/v1/ready` endpoint (added `database` dependency + `postgis` metadata).
* A **Docker Compose** `postgres-postgis` service (PostGIS 16 / 3.4) for local dev.
* Offline (no-DB-required) **pytest** coverage plus a gated **integration** suite.

**Out of scope (later phases, B3+):** India/state/district/sub-district boundary
tables and seed data, weather observation tables, NWP grid tables, crop/alert
reference tables, GIS analytics, spatial query engines.

---

## 2. Non-Negotiable Design Decisions

1. **The LLM is never the source of weather truth — and neither is the DB schema
   invented ad hoc.** Every stored entity in later phases must trace to an approved
   spec (`09_GIS_SPEC.md`, `10_DATABASE_SCHEMA.md`).
2. **No connections at import time.** Importing any `app.db` module must never open
   a database connection. Engines are created lazily during application startup.
3. **Async / asyncpg only.** All runtime access uses the `postgresql+asyncpg` URL,
   derived automatically from the configured `DATABASE_URL` (any driver scheme is
   normalised to `postgresql+asyncpg`).
4. **Deterministic engines stay out of the database layer.** B2 adds no analytics;
   FAO-56 / Mann-Kendall / spatial joins belong to `app/analytics` / `app/gis` (B4/B6).
5. **Never leak credentials.** The engine never logs its URL; `hide_parameters=True`;
   probe messages, migration output, and test fixtures must never contain secrets.
6. **Migrations are explicit, never auto-`destructive`.** B2 does not run migrations
   at application startup. Schema changes are applied via `alembic upgrade head`.
7. **The canonical storage CRS is EPSG:4326** (see `09_GIS_SPEC.md`). Metric work
   (distance/buffering) happens inside query expressions in EPSG:3857, never by
   overwriting the stored SRID.

---

## 3. Module Layout (`app/db/`)

```text
app/db/
├── __init__.py                # package marker / public re-exports (none heavy)
├── base.py                    # DeclarativeBase + TimestampMixin
├── session.py                 # async engine/factory/dispose helpers
├── spatial.py                 # geometry()/geography() + SRID + type aliases
├── health.py                  # DatabaseProbe (readiness)
├── service.py                 # DatabaseService (ownership boundary)
├── repositories/
│   ├── __init__.py
│   └── base.py                # generic BaseRepository[T]
├── models/
│   └── __init__.py            # placeholder package (B3+ adds domain models)
└── migrations/
    ├── env.py                 # async, environment-driven Alembic env
    ├── script.py.mako
    └── versions/
        └── 0001_enable_postgis.py
```

---

## 4. Configuration (Settings additions)

B2 adds the following fields to `app/config.py` (all env-driven, with safe local
defaults):

| Field | Environment | Default |
| :--- | :--- | :--- |
| `database_url` | `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/weathergpt` |
| `database_pool_size` | `DATABASE_POOL_SIZE` | `10` |
| `database_max_overflow` | `DATABASE_MAX_OVERFLOW` | `5` |
| `database_pool_timeout` | `DATABASE_POOL_TIMEOUT` | `10.0` (s) |
| `database_pool_recycle` | `DATABASE_POOL_RECYCLE` | `1800` (s) |
| `database_echo` | `DATABASE_ECHO` | `False` |
| `database_url_scheme` | `DATABASE_URL_SCHEME` | `postgresql+asyncpg` |

The `async_database_url` property normalises the configured `database_url` to the
`postgresql+asyncpg://` scheme (`postgresql://`, `postgresql+psycopg2://`,
`postgresql+psycopg://`, and `postgres://` are all accepted).

---

## 5. Async Engine & Session Factory (`app/db/session.py`)

* `create_async_engine_from_settings(settings)` — lazily builds an `AsyncEngine`
  with pooling (`pool_size`, `max_overflow`, `pool_timeout`, `pool_recycle`),
  `pool_pre_ping=True`, `future=True`, `hide_parameters=True`; **never logs the URL**.
* `create_session_factory(engine)` — returns an `async_sessionmaker` bound to the
  engine (`expire_on_commit=False`, `autoflush=False`). Callers are responsible for
  commit/rollback and close.
* `dispose_engine(engine)` — graceful, idempotent pool disposal; safe with `None`.

### Per-request session dependency

`app/dependencies/providers.py::get_db_session` yields a request-scoped
`AsyncSession` (or `None` in an environment where the database is not initialised —
the B1 test environment). On success it commits; on any exception it rolls back and
re-raises. This keeps route handlers free of explicit transaction plumbing.

---

## 6. Spatial Types (`app/db/spatial.py`)

```python
MultiPolygon   # geometry("MultiPolygon",  srid=4326)  -> MULTIPOLYGON
Polygon        # geometry("Polygon",       srid=4326)
Point          # geometry("Point",         srid=4326)
MultiLineString# geometry("MultiLineString",srid=4326)
geography()    # Geography (spherical, metric-aware), srid=4326
```

* `DEFAULT_SRID = 4326`, with `SRID_3857` available for metric query expressions.
* All storage columns are EPSG:4326 with a GIST spatial index.
* B2 ships **no** concrete spatial models — these type helpers are the contract that
  B3 (boundaries) and B4 (GIS) will use.

---

## 7. Repository Foundation (`app/db/repositories/base.py`)

`BaseRepository[T]` is a thin, dependency-injected generic over a model and a session:

* `get(pk)` / `list()`
* `get_by(**filters)` (scalar)
* `add(obj)` / `add_all(objs)` / `flush()` / `refresh(obj)`
* `delete(obj)`
* `commit()` / `rollback()` (explicit — the repository **never commits implicitly**)

It performs no DDL and holds no engine reference; it only wraps a session. Domain
repositories in later phases extend it.

---

## 8. Readiness Probe (`app/db/health.py`)

`DatabaseProbe` (name `"database"`):

1. `SELECT 1` — basic connectivity + query execution.
2. `SELECT extname FROM pg_extension WHERE extname = 'postgis'` — extension presence.
3. `SELECT postgis_version()` — version string (carried as `metadata["postgis"]`).

It is **safe by construction**: never exposes a URL/credentials/traceback, and any
exception yields `ok=False` with `detail="database unavailable"`. It does not run
expensive queries, so `/ready` stays fast.

The probe surfaces on `GET /api/v1/ready` as the `database` dependency, alongside
the B1 `application` probe. `DependencyStatus` gained an optional `postgis` field
(backward-compatible; only the `database` probe populates it).

---

## 9. DatabaseService & Composition Root

`DatabaseService(settings, engine=None)` owns the engine, session factory, and probe:

* `initialize()` — lazily creates engine + factory + probe (only called at startup).
* `session_context()` — async context manager yielding a bound `AsyncSession`.
* `probe` — the readiness probe used by `/ready`.
* `dispose()` — idempotent graceful shutdown.

It is wired into `AppContainer`:
* `container.database_service` (initialised lazily with `settings`);
* `container.adispose()` disposes the database service on shutdown;
* `app.dependencies.providers.get_database_service` reads it from `app.state`.

**Production-safety guard:** engine initialisation and `DatabaseProbe` registration
are gated on `app_env != "test"`. This keeps the B1 test environment (which asserts
a purely-`application` `/ready`) green.

---

## 10. Migrations (Alembic)

`alembic.ini` lives at the repo root (`script_location = app/db/migrations`). The
URL in `alembic.ini` is a placeholder — `app/db/migrations/env.py` injects
`Settings.async_database_url` so there is a single source of truth.

Initial migration `0001_enable_postgis.py`:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

down-revision is `None`. The migration is deliberately **non-destructive** (no drop
database / truncate / destructive DDL) as required by `10_DATABASE_SCHEMA.md` §8.

Apply via:

```powershell
docker compose up -d postgres-postgis
alembic upgrade head
```

---

## 11. Docker Compose (`postgres-postgis`)

* Image: `postgis/postgis:16-3.4`.
* Credentials/db name are env-driven (`POSTGRES_DB`, `POSTGRES_USER`,
  `POSTGRES_PASSWORD`), safe placeholders for local dev.
* Named volume `pgdata` for data persistence; healthcheck waits for both
  `pg_isready` and the PostGIS extension.
* Host port is configurable via `DB_HOST_PORT` (default `5432`) so it can be
  moved off an occupied local port (e.g. a native PostgreSQL on 5432 → set
  `DB_HOST_PORT=5433`).

---

## 12. Testing Strategy

**Offline unit suite (`tests/test_database_foundation.py`, 25 tests)** — no live DB:
settings/URL conversion, lazy engine creation, session factory, the offline
session-dependency path (yields `None`), repository foundation, PostGIS spatial type
configuration, probe offline/unavailable/postgis-missing behaviour, migration file
safety, no-credential-leak guarantees, and placeholder defaults.

**Integration suite (`tests/test_database_integration.py`, gated by the
`integration` marker)** — requires a reachable PostGIS:
* real probe finds PostGIS;
* `SELECT 1` through a real session;
* repository create/insert/select/drop against a dedicated test table;
* `/api/v1/ready` reports `database` connected + `postgis >= 3`.

**Windows/asyncpg note:** pytest-asyncio is configured in **strict** mode with
session-scoped loops (`asyncio_default_test_loop_scope` and
`asyncio_default_fixture_loop_scope = session`). The integration `engine` fixture is
an async fixture so asyncpg's pooled connections are created and reused inside the
same event loop that the tests run in (prevents "Event loop is closed" on the
Proactor event loop).

Integration tests are skipped automatically when the database is unreachable, so an
environment without PostGIS still passes the full suite (with skips).

---

## 13. Verification Summary

| Check | Command | Result |
| :--- | :--- | :--- |
| Offline B2 suite | `pytest tests/test_database_foundation.py -q` | 25 passed |
| Live readiness | `docker compose up -d postgres-postgis` → `alembic upgrade head` → `/ready` | `database` connected, `postgis` populated |
| Integration suite | `pytest -m integration -v` (DB up) | 4 passed |
| Full suite (DB up) | `pytest -q` | 244 passed |
| Compose validity | `docker compose config --quiet` | exit 0 |

---

## 14. Out of Scope (explicitly deferred)

B3 India/state/district/sub-district boundary tables + polygon seed data; B4 GIS
spatial handlers; B5 NWP tables; weather observation/ingest tables; crop and IMD
alert reference tables; deterministic analytics engines; production cloud topology.

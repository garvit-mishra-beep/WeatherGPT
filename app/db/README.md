# Database Layer (`app/db/`)

## 1. Purpose
Own the PostgreSQL + PostGIS storage foundation for WeatherGPT: the async engine,
session management, migration pipeline, spatial column types, repository base, and
a readiness probe — with no domain tables (those arrive in B3+).

## 2. Modules
| Module | Responsibility |
| :--- | :--- |
| `base.py` | `Base` (SQLAlchemy 2.x DeclarativeBase) + `TimestampMixin` (`created_at`/`updated_at`). |
| `session.py` | Lazy pooled `AsyncEngine` (asyncpg), `async_sessionmaker`, `dispose_engine`. |
| `spatial.py` | `geometry()` / `geography()` helpers, `DEFAULT_SRID=4326`, `MultiPolygon`/`Polygon`/`Point`/`MultiLineString` aliases. |
| `health.py` | `DatabaseProbe` — `SELECT 1` + PostGIS presence/version; surfaced on `/ready`. |
| `service.py` | `DatabaseService` ownership boundary (engine + factory + probe), disposed on shutdown. |
| `repositories/base.py` | Generic `BaseRepository[T]` (explicit commit/rollback only). |
| `models/` | Placeholder package — domain models land in B3+. |
| `migrations/` | Alembic env (async, environment-driven) + version scripts. |

## 3. Key Guarantees
- **No connections at import time** — engines are created lazily at startup.
- **Never logs the connection URL** (`hide_parameters=True`).
- **Non-destructive migrations only** — B2 enables the `postgis` extension; no
  destructive DDL. Never auto-run migrations from application startup.
- **Canonical storage CRS is EPSG:4326** (see `docs/09_GIS_SPEC.md`).

## 4. Wiring (B2)
`DatabaseService` is constructed by `AppContainer` during lifespan startup and
disposed via `container.adispose()` on shutdown. Routes depend on an
`AsyncSession` via `app.dependencies.providers.get_db_session`, or on the service
via `get_database_service`. Registration is gated on `app_env != "test"`.

## 5. Local & Native Setup (No Docker)
```powershell
# Set DATABASE_URL to your native PostgreSQL 16 + PostGIS 3.4 instance
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5433/weathergpt"
alembic upgrade head
pytest -q
```

## 6. Testing
- `tests/test_database_foundation.py` — unit coverage for connection pool, session, models.
- `tests/test_database_integration.py` — live PostGIS integration tests for spatial queries.

# 46 — Database Hardening & Resilience (B13.5)

**Document:** `docs/46_DATABASE_HARDENING.md`  
**Milestone:** B13.5 — Database Hardening  
**Components:** `app/db/session.py`, `app/db/service.py`, `app/db/health.py`, `app/config.py`, `app/dependencies/providers.py`

---

## 1. Executive Summary

Milestone **B13.5** hardens the PostgreSQL 16 + PostGIS 3.4 database layer against connection exhaustion, hung queries, uncommitted transaction leaks, and silent readiness false-positives without introducing heavy second abstractions or destructive schema mutations.

---

## 2. Configurable Connection Pool & Bounded Timeouts

All database connection pool knobs and operational timeouts are strictly managed by `Settings` (`app/config.py`) and applied during engine instantiation (`app/db/session.py`):

| Parameter | Settings Key | Default | Purpose |
| :--- | :--- | :--- | :--- |
| **Pool Size** | `database_pool_size` | `10` | Base async connection pool per worker |
| **Max Overflow** | `database_max_overflow` | `5` | Peak burst connections allowed beyond base pool |
| **Pool Timeout** | `database_pool_timeout` | `10.0s` | Bounded wait duration when acquiring connection |
| **Pool Recycle** | `database_pool_recycle` | `1800s` | Connection lifetime before recycle (prevents stale TCP) |
| **Pre-Ping** | `pool_pre_ping=True` | `True` | Validates live connection health before lease |
| **Command Timeout** | `database_command_timeout`| `30.0s` | Bounded statement duration preventing hung queries |
| **Connect Timeout** | `database_connect_timeout`| `10.0s` | Bounded socket handshake timeout |

### asyncpg Connection Arguments
```python
connect_args = {
    "timeout": settings.database_connect_timeout,
    "command_timeout": settings.database_command_timeout,
}
```

---

## 3. Transaction Safety & Lifecycle Guarantees

### 3.1 `DatabaseService.session_context()`
```python
@asynccontextmanager
async def session_context(self) -> AsyncGenerator[AsyncSession, None]:
    if self._session_factory is None:
        raise RuntimeError("DatabaseService is not initialized")
    async with self._session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

* **Clean Completion:** Commits staged operations automatically.
* **Error / Exception:** Automatically rolls back transactions, clearing session state so the underlying pooled connection is never returned in an aborted/broken transaction state.
* **Always Closed:** Context manager ensures session cleanup on exit, eliminating connection pool leaks.

### 3.2 Request-Scoped Dependency (`get_db_session`)
`get_db_session` provides a request-bound `AsyncSession` yielding to endpoints, committing on normal completion and rolling back on any caught exception.

---

## 4. PostGIS Indexing & Spatial Query Performance

Spatial models (`SpatialCountry`, `SpatialState`, `SpatialDistrict`, `SpatialSubDistrict` in `app/db/models/boundaries.py`) feature:
1. **Primary Key B-Trees:** Unique code lookups (`country_code`, `state_code`, `district_code`, `subdistrict_code`) $< 1\text{ ms}$.
2. **Foreign Key Indexes:** Cascading hierarchy traversal with explicit `index=True`.
3. **GiST Spatial Indexes:** PostGIS `MultiPolygon` in EPSG:4326 indexed via GiST for sub-5ms `ST_Contains` / `ST_Covers` point-in-polygon queries.

---

## 5. Health & Readiness Probe Hardening

`DatabaseProbe` (`app/db/health.py`):
* Evaluates `SELECT 1`, verifies `postgis` extension presence, and reads PostGIS version.
* Catches connection refusal and pool acquisition timeouts gracefully.
* When the database is down, `/ready` reports `status="not_ready"` with `ready=False`.
* Provider failures never trigger database readiness failures.

---

## 6. Verification & Test Evidence

* Hardened pool configurations, connect_args, pre-ping: `tests/test_database_hardening.py` (7/7 passed).
* Transaction commit on success, rollback on exception, idempotent disposal verified.
* Full test regression suite: 504 passed, 21 skipped.

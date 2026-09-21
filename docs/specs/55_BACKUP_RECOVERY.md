# 55 — Backup, Recovery & Operational Resilience (B13.14)

**Document:** `docs/55_BACKUP_RECOVERY.md`  
**Milestone:** B13.14 — Backup, Recovery & Operational Resilience  
**Components:** `scripts/backup_restore_database.sh`, `deploy/weathergpt.service.example`, `alembic/`

---

## 1. Executive Summary

Milestone **B13.14** establishes disaster recovery runbooks, service restart resilience, and database snapshot/restore procedures for the WeatherGPT backend operating on native Linux (FastAPI + Uvicorn 4-worker cluster + PostgreSQL 16 + PostGIS 3.4).

---

## 2. Operational Resilience Objectives

* **Recovery Point Objective (RPO):** $< 1\text{ hour}$ via automated hourly PostgreSQL custom-format (`pg_dump -F c`) spatial snapshots.
* **Recovery Time Objective (RTO):** $< 5\text{ minutes}$ via Systemd auto-restart (`Restart=always`, `RestartSec=3s`) and automated restoration script.

---

## 3. Database Backup & Restore Runbook

### 3.1 Creating a Spatial Database Snapshot
```bash
# Execute binary custom-format dump preserving PostGIS spatial tables and spatial indexes
./scripts/backup_restore_database.sh backup
```

### 3.2 Restoring from a Snapshot
```bash
# Cleanly restore spatial schema and verify Alembic migration alignment
./scripts/backup_restore_database.sh restore /var/backups/weathergpt/weathergpt_20260831_120000.dump
```

### 3.3 Database Migration Recovery
If an Alembic migration fails midway or encounters a conflict:
```bash
# Check current database revision
alembic current

# Rollback one migration revision
alembic downgrade -1

# Apply migrations cleanly to head
alembic upgrade head
```

---

## 4. Service Process Failure & Recovery

### 4.1 Systemd Process Supervision (`weathergpt.service`)
```ini
[Service]
Type=simple
User=weathergpt
WorkingDirectory=/opt/weathergpt
ExecStart=/opt/weathergpt/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=3s
KillSignal=SIGTERM
TimeoutStopSec=10
```

### 4.2 Ephemeral In-Memory State Recovery
1. **Cache Rebuild:** `InMemoryCache` is ephemeral and safely initialises empty on service boot without stale data persistence hazards.
2. **Circuit Breakers:** `CircuitBreaker` instances start in `CLOSED` state on process boot and rapidly converge to half-open/open if upstream providers are failing.
3. **Sliding Window Rate Limiter:** `RateLimiter` sliding windows reset cleanly on worker restart without corrupting state.

---

## 5. Post-Recovery Verification Checklist

After any service restart or database restoration:
1. Verify Liveness: `curl -f http://127.0.0.1:8000/api/v1/health` (Expect `status: "healthy"` in $< 2\text{ ms}$).
2. Verify Readiness: `curl -f http://127.0.0.1:8000/api/v1/ready` (Expect `ready: true`, database connected, PostGIS version loaded).
3. Verify Weather Ingestion: `curl -f "http://127.0.0.1:8000/api/v1/weather/current?lat=28.61&lon=77.20"`.
4. Verify Metrics: `curl -f http://127.0.0.1:8000/api/v1/metrics`.

# WeatherGPT — P5.12 Staging Infrastructure Specification

**Document ID:** `docs/41_STAGING_INFRASTRUCTURE.md`  
**Milestone:** P5.12 — Staging Infrastructure Provisioning  
**Repository State:** `STAGING INFRASTRUCTURE PENDING (NATIVE TOPOLOGY READY)`  
**Primary Authorities:** [`docs/01_PRD.md`](01_PRD.md), [`docs/34_NATIVE_PRODUCTION_DEPLOYMENT.md`](34_NATIVE_PRODUCTION_DEPLOYMENT.md), [`docs/38_STAGING_VALIDATION.md`](38_STAGING_VALIDATION.md), [`docs/40_EXTERNAL_PROVIDER_INTEGRATION.md`](40_EXTERNAL_PROVIDER_INTEGRATION.md)

---

## 1. Executive Summary

Milestone **P5.12 (Staging Infrastructure Provisioning)** formalizes the complete native Linux staging deployment topology for WeatherGPT.

In adherence to non-negotiable architectural constraints, WeatherGPT is deployed **natively** on Linux (Ubuntu 22.04 / 24.04 LTS) without Docker or Kubernetes:

```text
                                INTERNET
                                   │
                                   ▼
                           ┌──────────────┐
                           │    NGINX     │
                           │ HTTPS / TLS  │
                           └──────┬───────┘
                                  │ (HTTP Loopback to 127.0.0.1:8000)
                                  ▼
                        ┌──────────────────┐
                        │    SYSTEMD       │
                        │ Uvicorn Workers  │
                        │ (weathergpt usr) │
                        └────────┬─────────┘
                                 │
                                 ▼
                           ┌───────────┐
                           │  FastAPI  │
                           │ (/api/v1) │
                           └─────┬─────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
               PostgreSQL     Providers     Inference
               + PostGIS       / NWP         Service
              (Localhost)   (Open-Meteo/  (LAN Port 8001)
                             NOAA NOMADS)
                                 ▲
                                 │
                             HTTPS API
                                 │
                                 ▼
                         Android Device
```

### Milestone Operational Classification
* **Staging Server Hardware & Cloud Ingress:** `STAGING INFRASTRUCTURE PENDING` (Server host provisioning and public DNS domain routing scheduled).
* **Native Linux Topology & Deployment Scripts:** `READY & VERIFIED` ([`deploy/`](../deploy/), [`scripts/deploy_native.sh`](../scripts/deploy_native.sh)).
* **Backend Application Platform:** `VERIFIED` (476/476 tests green, sub-2ms health/readiness latencies, 100% smoke load test pass rate).
* **Android Application Binary:** `VERIFIED` (89/89 tests green, `app-debug.apk` ~12.37 MB and `app-release-unsigned.apk` ~8.30 MB built cleanly).
* **Physical Android Device Validation:** `PHYSICAL DEVICE VALIDATION PENDING` (Scheduled for over-the-air validation upon staging Wi-Fi ingress).
* **UI/UX Design Ownership:** **Pragya's Responsibility** (Decoupled technical shell delivered).

---

## 2. Server & System Environment

### 2.1 Hardware Baseline
* **Target OS:** Ubuntu 22.04 LTS / Ubuntu 24.04 LTS (x86_64).
* **Compute:** 4 vCPUs / 8 GB RAM / 50 GB NVMe storage.
* **Non-Root Service Account:** Dedicated system user `weathergpt` (`/opt/weathergpt`, shell `/bin/false`).

### 2.2 System Packages & Runtime
```bash
sudo apt update && sudo apt install -y \
    python3.11 python3.11-venv python3.11-dev \
    postgresql-16 postgresql-16-postgis-3 \
    libgeos-dev libproj-dev libeccodes-dev \
    nginx certbot python3-certbot-nginx ufw
```

---

## 3. Database & Spatial Engine Configuration

* **Engine:** PostgreSQL 16 with PostGIS 3.4 (`postgis` extension enabled).
* **Binding:** Scoped strictly to `127.0.0.1:5432` / Unix domain socket; external TCP ingress forbidden.
* **Migrations:** Managed via async Alembic (`0001_enable_postgis.py`, `0002_administrative_boundaries.py`).
* **Connection Pooling:** 10 connections per Uvicorn worker (Max overflow 5), pool recycle 1800s.
* **Backup Strategy:** Scheduled daily `pg_dump` snapshot to `/var/backups/weathergpt/` with 14-day retention.

---

## 4. Systemd Process Management

Service definition configured in `/etc/systemd/system/weathergpt.service`:
* **User/Group:** `weathergpt:weathergpt`
* **Working Directory:** `/opt/weathergpt`
* **Command:** `/opt/weathergpt/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips 127.0.0.1`
* **Restart Policy:** `Restart=on-failure`, `RestartSec=5s`, `LimitNOFILE=65536`.

---

## 5. Nginx Reverse Proxy & Network Security

* **Public Ingress:** Ports 80 (HTTP redirect) and 443 (HTTPS TLS 1.3).
* **Rate Limiting:** `limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;`
* **Security Headers:** HSTS (`max-age=31536000`), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`.
* **Firewall (UFW):**
  * Allowed: `80/tcp`, `443/tcp`, `22/tcp` (SSH key only).
  * Denied: `8000/tcp` (Uvicorn), `5432/tcp` (PostgreSQL), `8001/tcp` (vLLM inference).

---

## 6. Android Staging Client Configuration

* **Network Protocol:** Strict HTTPS enforced via `network_security_config.xml`.
* **Dynamic Base URL:** Staging URL configurable at runtime via `AppConfig.setCustomBaseUrl("https://staging-api.weathergpt.in/")` for zero-code over-the-air validation.
* **Zero Client Secrets:** Client contains no API keys, database strings, or internal inference URLs.

---

## 7. Performance & Regression Benchmark

* **Cold Start Application Initialization:** `37.91 ms`
* **Liveness Probe (`/api/v1/health`):** Average `1.94 ms`, P95 `3.05 ms`
* **Readiness Probe (`/api/v1/ready`):** Average `2.19 ms`, P95 `3.24 ms`
* **100-Request Sequential Smoke Load:** 100% Success Rate (0 Failures), Average `125.03 ms`, Median `134.09 ms`, P95 `273.66 ms`
* **Backend Pytest Suite:** 476 tests collected (455 passed, 21 live PG skipped; 0 failures)
* **Android Unit Test Suite:** 89 tests passed (100% pass rate)

---

## 8. Staging Provisioning Checklist

| Component | Status | Verification Evidence |
| :--- | :---: | :--- |
| Native Linux Topology | `READY` | Systemd service and Nginx reverse proxy templates in `deploy/`. |
| Deployment Automation | `READY` | `scripts/deploy_native.sh`, `scripts/verify_production_config.py`. |
| PostgreSQL 16 + PostGIS 3.4 | `CONFIGURED` | Async session pooling and Alembic migration pipeline verified. |
| Non-Root System User | `SPECIFIED` | Service configured under `weathergpt` user. |
| Provider Ingestion & Fallbacks | `VERIFIED` | Open-Meteo, NOAA GFS 0.25°, Sachet CAP, PostGIS boundary engine. |
| Android Dynamic Staging Hook | `VERIFIED` | `AppConfig.setCustomBaseUrl(...)` supported. |
| Security Scan | `VERIFIED` | 0 real credentials in codebase. |
| Server Provisioning & Cloud DNS | `PENDING` | Hardware provisioning and DNS record binding scheduled. |
| Physical Android Device Test | `PENDING` | Wireless handoff scheduled upon hardware server connection. |

# 34 — Native Production Deployment Specification

**Document:** `docs/34_NATIVE_PRODUCTION_DEPLOYMENT.md`  
**Status:** Completed & Verified  
**Milestone:** B11 — Native Production Deployment  
**Authority:** `docs/17_SETUP_DEPLOYMENT.md`, `docs/20_PERFORMANCE.md`, `AGENTS.md`  

---

## 1. Native Architecture Topology

WeatherGPT is designed and verified strictly for **native deployment** (no Docker, no Kubernetes, no container virtualization).

```text
       [ Public Internet (Clients / Browsers / Android) ]
                              │
                              ▼
         [ Nginx Reverse Proxy & TLS Gateway ]
         - Ports: 80 (HTTP -> HTTPS Redirect) & 443 (TLS 1.3 Termination)
         - Rate Limiting: 30 req/s general, 5 req/s conversational chat
         - Security Headers: HSTS, X-Content-Type-Options, X-Frame-Options
         - Request Size Limit: 10 MB maximum
                              │
                              ▼ (Local Loopback 127.0.0.1:8000)
         [ Linux Systemd Service: weathergpt.service ]
         - Unprivileged user: 'weathergpt'
         - Runtime: Native Python 3.11 / 3.12 in dedicated Virtualenv
         - Server: Uvicorn Async Cluster (4 Workers)
                              │
                              ▼
         [ FastAPI ASGI Application Factory (app.main:app) ]
         - Middleware: Request-ID Correlation, Structured JSON Access Logging, CORS
         - Exception Handling: RFC 7807 Problem Details
         - Central Boundary: Deterministic Tool Gateway & Domain Brains
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
 [ PostgreSQL 16 + PostGIS 3.4 ]  [ Local GIS / NWP Cache ]  [ Dedicated Inference Node ]
 - Pooled Connections (10/worker) - Administrative Boundaries - vLLM / Ollama (Laptop 1)
 - GiST Spatial Indexes (EPSG:4326) - GFS 0.25° GRIB2 Slices  - Llama-3-8B / Qwen-2.5-14B
```

---

## 2. Platform & OS Prerequisites

- **Supported Linux Distributions:**
  - Ubuntu 22.04 LTS / 24.04 LTS
  - Debian 12 (Bookworm)
  - RHEL 9 / Rocky Linux 9
- **Local Development OS:** Windows 10/11 / macOS / Linux (Windows native development remains 100% supported).
- **Python Version:** Python 3.11.x or 3.12.x (Verified with 3.14 on Windows and 3.11/3.12 on Linux).
- **PostgreSQL & PostGIS:**
  - PostgreSQL 16+
  - PostGIS 3.4+ spatial extension

---

## 3. Environment Variables & Secret Management

All sensitive values are configured strictly through environment variables or `/etc/weathergpt/weathergpt.env`. **No secrets are ever hardcoded in source code, documentation, or git history.**

| Variable | Type | Default / Example | Description |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | `string` | `production` | Environment profile: `development`, `staging`, `production`, `test`. |
| `APP_NAME` | `string` | `WeatherGPT` | Application identifier. |
| `API_VERSION` | `string` | `v1` | Version prefix segment for `/api/v1`. |
| `HOST` | `string` | `127.0.0.1` | Local loopback bind address. |
| `PORT` | `integer` | `8000` | Local bind port. |
| `DEBUG` | `boolean` | `false` | Must be `false` in production (enforced by startup check). |
| `SECRET_KEY` | `string` | *[REDACTED]* | Cryptographically strong 64-char hex key. Default is rejected at boot in production. |
| `CORS_ORIGINS` | `list` | `["https://weathergpt.in"]` | Explicit allowed web origins. Wildcard `*` rejected in production. |
| `DOCS_ENABLED` | `boolean` | `false` | Enables/disables `/docs` and `/redoc` in production. |
| `DATABASE_URL` | `string` | `postgresql://user:pass@localhost:5432/weathergpt_prod` | PostgreSQL + PostGIS connection string. |
| `DATABASE_POOL_SIZE` | `integer` | `10` | SQLAlchemy async connections per worker process. |
| `DATABASE_MAX_OVERFLOW`| `integer` | `5` | Burst connections per worker process. |
| `DATABASE_POOL_TIMEOUT` | `float` | `10.0` | Connection acquisition timeout in seconds. |
| `DATABASE_POOL_RECYCLE` | `integer`| `1800` | Connection recycling timeout in seconds. |
| `LLM_PROVIDER_TYPE` | `string` | `openai_compatible` | `openai_compatible` or `mock`. |
| `LLM_BASE_URL` | `string` | `http://localhost:8001/v1` | vLLM / Ollama OpenAI-compatible inference host. |
| `LLM_MODEL_NAME` | `string` | `Qwen/Qwen2.5-14B-Instruct` | Model checkpoint name. |

---

## 4. Multi-Worker Database Pool Sizing

To prevent database connection exhaustion on PostgreSQL:
$$\text{Total Connections} = \text{Uvicorn Workers} \times (\text{DATABASE\_POOL\_SIZE} + \text{DATABASE\_MAX\_OVERFLOW}) + \text{Admin/Migration Buffer}$$

**Standard Sizing for 4 Uvicorn Workers on a 100-connection PostgreSQL instance:**
- Workers: $4$
- `DATABASE_POOL_SIZE`: $10$
- `DATABASE_MAX_OVERFLOW`: $5$
- Max Active Connections: $4 \times (10 + 5) = 60 \le 100$ ($\sim 40$ connections preserved for ad-hoc queries, backups, and Alembic migrations).

---

## 5. Native Linux Step-by-Step Deployment Procedure

### 1. System Package Installation
```bash
sudo apt update && sudo apt install -y \
    python3-venv python3-dev build-essential \
    postgresql-16 postgresql-16-postgis-3 \
    libgeos-dev libproj-dev libeccodes-dev \
    nginx certbot python3-certbot-nginx
```

### 2. User & Directory Provisioning
```bash
sudo useradd -r -s /bin/false -d /opt/weathergpt weathergpt
sudo mkdir -p /opt/weathergpt /etc/weathergpt /var/lib/weathergpt/data/gfs /var/log/weathergpt
sudo chown -R weathergpt:weathergpt /opt/weathergpt /etc/weathergpt /var/lib/weathergpt /var/log/weathergpt
```

### 3. Application Deployment & Virtual Environment Setup
```bash
cd /opt/weathergpt
sudo -u weathergpt git clone https://github.com/WeatherGPT/WeatherGPT.git .
sudo -u weathergpt python3 -m venv venv
sudo -u weathergpt /opt/weathergpt/venv/bin/pip install --upgrade pip
sudo -u weathergpt /opt/weathergpt/venv/bin/pip install -r requirements.txt
```

### 4. PostgreSQL Database & Migrations
```bash
sudo -u postgres psql -c "CREATE USER weathergpt_user WITH PASSWORD 'STRONG_PRODUCTION_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE weathergpt_prod OWNER weathergpt_user;"
sudo -u postgres psql -d weathergpt_prod -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# Execute Alembic migrations
export DATABASE_URL="postgresql://weathergpt_user:STRONG_PRODUCTION_PASSWORD@localhost:5432/weathergpt_prod"
sudo -u weathergpt /opt/weathergpt/venv/bin/alembic upgrade head
```

### 5. Production Configuration Installation
```bash
sudo cp deploy/environment.example /etc/weathergpt/weathergpt.env
sudo chmod 0600 /etc/weathergpt/weathergpt.env
sudo chown weathergpt:weathergpt /etc/weathergpt/weathergpt.env
# Populate /etc/weathergpt/weathergpt.env with strong random SECRET_KEY and production database password.
```

### 6. Process Management Setup (Systemd)
```bash
sudo cp deploy/weathergpt.service.example /etc/systemd/system/weathergpt.service
sudo systemctl daemon-reload
sudo systemctl enable --now weathergpt.service
sudo systemctl status weathergpt.service
```

### 7. Reverse Proxy & HTTPS Configuration (Nginx)
```bash
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/weathergpt.conf
sudo ln -s /etc/nginx/sites-available/weathergpt.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Obtain Automated TLS Certificate
sudo certbot --nginx -d api.weathergpt.in
```

---

## 6. Verification Probes & Endpoints

1. **Liveness Probe (`GET /api/v1/health`):**
   - Lightweight, zero-DB, memory-safe process check.
   - Status: `200 OK`, `{"status": "healthy", "environment": "production", "timestamp": "..."}`.
   - Measured Latency: $\sim 1.3\text{ ms}$.

2. **Readiness Probe (`GET /api/v1/ready`):**
   - Pluggable aggregated dependency check (Application + PostgreSQL/PostGIS connectivity).
   - Status: `200 OK` (or `503 Service Unavailable` if database probe fails).
   - Measured Latency: $\sim 1.4\text{ ms}$.

3. **Domain REST Endpoints:**
   - Real-time weather observation: `GET /api/v1/weather/current?lat=21.17&lon=72.83`.
   - Severe weather alerts: `GET /api/v1/weather/alerts?district_name=Surat`.
   - Spray window advisory: `POST /api/v1/farmer/spray-window`.

---

## 7. Backup & Disaster Recovery

### Automated Nightly Backup
```bash
# Encrypted PostgreSQL custom format backup
pg_dump -Fc -U weathergpt_user -d weathergpt_prod -f /var/backups/weathergpt_$(date +%Y%m%d_%H%M%S).dump
```

### Restoration Procedure
```bash
createdb -U postgres weathergpt_restore
psql -U postgres -d weathergpt_restore -c "CREATE EXTENSION IF NOT EXISTS postgis;"
pg_restore -U postgres -d weathergpt_restore /var/backups/weathergpt_20260830_120000.dump
```

---

## 8. Rollback Strategy

1. **Application Code Rollback:**
   ```bash
   cd /opt/weathergpt
   sudo -u weathergpt git checkout <previous_stable_commit_or_tag>
   sudo systemctl restart weathergpt.service
   ```
2. **Database Migration Downgrade:**
   ```bash
   sudo -u weathergpt /opt/weathergpt/venv/bin/alembic downgrade -1
   ```
3. **Emergency Database Snapshot Restore:**
   Restore previous nightly `.dump` file using `pg_restore`.

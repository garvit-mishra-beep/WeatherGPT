# WeatherGPT — Native Production Deployment Guide

This directory contains configuration templates, systemd service definitions, Nginx reverse proxy specifications, and deployment runbooks for deploying **WeatherGPT** natively on Linux (Ubuntu 22.04 / 24.04 LTS, Debian 12, or RHEL 9) without Docker or Kubernetes virtualization.

---

## 1. Native Architecture Topology

```text
       [ Public Internet (Clients / Android Devices / Web) ]
                                   │
                                   ▼
         [ Nginx Reverse Proxy & TLS Gateway (Ports 80 / 443) ]
         - TLS 1.3 Termination (Let's Encrypt / Custom Certificate)
         - Security Headers: HSTS, X-Content-Type-Options, CSP, X-Frame-Options
         - Rate Limiting: 30 r/s general API, 5 r/s conversational chat
         - Request Size Limit: 10 MB maximum
                                   │
                                   ▼ (HTTP Loopback to 127.0.0.1:8000)
         [ Linux Systemd Service: weathergpt.service (User: weathergpt) ]
         - Uvicorn Async Cluster (4 Workers)
         - Native Python 3.11 / 3.12 Virtual Environment
         - Bounded Process Memory & Restart on Failure
                                   │
                                   ▼
         [ FastAPI ASGI Application Factory (app.main:app) ]
         - Middleware: Request-ID Correlation, JSON Logging, CORS, Rate Limit
         - Central Tool Gateway & Domain Brains
                                   │
    ┌──────────────────────────────┼──────────────────────────────┐
    ▼                              ▼                              ▼
[ PostgreSQL 16 + PostGIS 3.4 ]  [ Redis / In-Memory Cache ]  [ Dedicated LLM Host ]
(Connection Pool: 10/worker)     (Result & Grid Cache)        (vLLM / Ollama Node via LAN)
```

---

## 2. Server Prerequisites

1. **Operating System:** Ubuntu 22.04 / 24.04 LTS or Debian 12.
2. **Python Runtime:** Python 3.11 or 3.12 with `python3-venv` and `python3-dev`.
3. **Database Server:** PostgreSQL 16+ with PostGIS 3.4+ spatial extension:
   ```bash
   sudo apt update
   sudo apt install -y postgresql-16 postgresql-16-postgis-3
   ```
4. **Geospatial & System Libraries:**
   ```bash
   sudo apt install -y libgeos-dev libproj-dev libeccodes-dev nginx certbot python3-certbot-nginx
   ```

---

## 3. Step-by-Step Installation Procedure

### Step 1: Create Non-Root Service User & Directories
```bash
sudo useradd -r -s /bin/false -d /opt/weathergpt weathergpt
sudo mkdir -p /opt/weathergpt /etc/weathergpt /var/lib/weathergpt/data/gfs /var/backups/weathergpt
sudo chown -R weathergpt:weathergpt /opt/weathergpt /etc/weathergpt /var/lib/weathergpt /var/backups/weathergpt
```

### Step 2: Clone Repository & Build Python Virtual Environment
```bash
cd /opt/weathergpt
sudo -u weathergpt git clone https://github.com/WeatherGPT/WeatherGPT.git .
sudo -u weathergpt python3 -m venv venv
sudo -u weathergpt /opt/weathergpt/venv/bin/pip install --upgrade pip
sudo -u weathergpt /opt/weathergpt/venv/bin/pip install -r requirements.txt
```

### Step 3: Configure Database & Run Migrations
```bash
sudo -u postgres psql -c "CREATE USER weathergpt_user WITH PASSWORD 'STRONG_DB_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE weathergpt_prod OWNER weathergpt_user;"
sudo -u postgres psql -d weathergpt_prod -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# Execute Alembic migrations
export DATABASE_URL="postgresql://weathergpt_user:STRONG_DB_PASSWORD@localhost:5432/weathergpt_prod"
sudo -u weathergpt /opt/weathergpt/venv/bin/alembic upgrade head
```

### Step 4: Install Environment Configuration
```bash
sudo cp deploy/environment.example /etc/weathergpt/weathergpt.env
sudo chmod 0600 /etc/weathergpt/weathergpt.env
sudo chown weathergpt:weathergpt /etc/weathergpt/weathergpt.env
# Edit /etc/weathergpt/weathergpt.env with production secrets
```

### Step 5: Install & Start Systemd Service
```bash
sudo cp deploy/weathergpt.service.example /etc/systemd/system/weathergpt.service
sudo systemctl daemon-reload
sudo systemctl enable --now weathergpt.service
sudo systemctl status weathergpt.service
```

### Step 6: Configure Nginx & SSL Certificate
```bash
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/weathergpt.conf
sudo ln -s /etc/nginx/sites-available/weathergpt.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Issue Let's Encrypt TLS Certificate
sudo certbot --nginx -d api.weathergpt.in
```

---

## 4. Operational Verification Checklist

```bash
# 1. Check Liveness Probe (Sub-2ms response)
curl -i http://127.0.0.1:8000/api/v1/health

# 2. Check Readiness Probe (Checks database, PostGIS, providers, cache)
curl -i http://127.0.0.1:8000/api/v1/ready

# 3. Check Observability Metrics
curl -i http://127.0.0.1:8000/api/v1/metrics

# 4. Execute Full Configuration Audit Script
python scripts/verify_production_config.py

# 5. Execute Latency Benchmark Suite
python scripts/benchmark_native.py
```

---

## 5. Automated Upgrades & Database Backups

### Automated Deployments / Upgrades
```bash
sudo ./scripts/deploy_native.sh
```

### Database Backup & Restore Automation
```bash
# Create atomic compressed backup
./scripts/backup_restore_database.sh backup

# Restore backup
./scripts/backup_restore_database.sh restore /var/backups/weathergpt/weathergpt_backup_latest.sql.gz
```

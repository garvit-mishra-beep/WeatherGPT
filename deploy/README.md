# WeatherGPT — Native Production Deployment Guide

This directory contains configuration templates and instructions for deploying WeatherGPT natively on Linux (Ubuntu 22.04 / 24.04 LTS, Debian 12, or RHEL 9) without Docker or Kubernetes.

---

## 1. Native Architecture Topology

```text
       [ Internet Traffic ]
                │
                ▼
       [ Nginx Reverse Proxy ]
       (TLS Termination / Rate Limiting / Security Headers on Ports 80 & 443)
                │
                ▼ (HTTP Loopback to 127.0.0.1:8000)
       [ Systemd Process Manager: weathergpt.service ]
       (Uvicorn 4-Worker Cluster running Python 3.11/3.12 under user 'weathergpt')
                │
                ▼
       [ FastAPI Application Engine ]
       (RFC 7807 Error Handling / Request-ID Tracing / Tool Gateway)
                │
    ┌───────────┼────────────────────────────────────────┐
    ▼           ▼                                        ▼
[ PostgreSQL 16 + PostGIS 3.4 ]              [ Dedicated LLM Host ]
(Connection Pool: 10 connections/worker)     (vLLM / Ollama Node via LAN)
```

---

## 2. Server Prerequisites

1. **Operating System:** Ubuntu 22.04 / 24.04 LTS or Debian 12.
2. **Python Runtime:** Python 3.11 or 3.12 with `python3-venv` and `python3-dev`.
3. **Database Server:** PostgreSQL 16+ with PostGIS 3.4+ extension:
   ```bash
   sudo apt update
   sudo apt install -y postgresql-16 postgresql-16-postgis-3
   ```
4. **Geospatial & GRIB2 System Libraries:**
   ```bash
   sudo apt install -y libgeos-dev libproj-dev libeccodes-dev nginx certbot python3-certbot-nginx
   ```

---

## 3. Step-by-Step Installation Procedure

### Step 1: Create Non-Root Service User & Directories
```bash
sudo useradd -r -s /bin/false -d /opt/weathergpt weathergpt
sudo mkdir -p /opt/weathergpt /etc/weathergpt /var/lib/weathergpt/data/gfs
sudo chown -R weathergpt:weathergpt /opt/weathergpt /etc/weathergpt /var/lib/weathergpt
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

## 4. Verification Checklist

```bash
# 1. Check Liveness Probe (Should return 200 {"status": "ok"})
curl -i http://127.0.0.1:8000/api/v1/health

# 2. Check Readiness Probe (Should return 200 {"ready": true, "probes": [...]})
curl -i http://127.0.0.1:8000/api/v1/ready

# 3. Check Real-Time Weather Observation API
curl -i "http://127.0.0.1:8000/api/v1/weather/current?latitude=21.17&longitude=72.83"
```

---

## 5. Database Backup & Disaster Recovery

### Automated Daily PostgreSQL Backup
```bash
# Backup command
pg_dump -Fc -U weathergpt_user -d weathergpt_prod -f /var/backups/weathergpt_$(date +%Y%m%d_%H%M%S).dump

# Restore command into a new database
createdb -U postgres weathergpt_restore
psql -U postgres -d weathergpt_restore -c "CREATE EXTENSION IF NOT EXISTS postgis;"
pg_restore -U postgres -d weathergpt_restore /var/backups/weathergpt_20260830_120000.dump
```

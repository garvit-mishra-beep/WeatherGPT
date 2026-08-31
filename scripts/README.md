# WeatherGPT Operational Scripts

**Directory:** `scripts/`  
**Purpose:** Native Linux deployment automation, production configuration audits, terminal QR pairing, load benchmarking, and database backup/recovery tools.

---

## 1. Overview of Scripts

| Script | Type | Purpose | Production Safe? |
| :--- | :--- | :--- | :--- |
| [`deploy_native.sh`](deploy_native.sh) | Bash | Non-destructive deployment and upgrade runner for native Linux hosts (Ubuntu/Debian/RHEL). | Yes (Non-destructive) |
| [`verify_production_config.py`](verify_production_config.py) | Python CLI | Audits environment variables, secret masking, PostgreSQL connectivity, and PostGIS extension status. | Yes (Read-only audit) |
| [`generate_backend_qr.py`](generate_backend_qr.py) | Python CLI | Generates in-terminal ASCII QR codes for Android LAN IP pairing. | Yes (Utility) |
| [`benchmark_native.py`](benchmark_native.py) | Python CLI | Measures cold-start time, health/readiness probe latencies, and smoke tests 20 core endpoints. | Yes (Read-only benchmarking) |
| [`benchmark_production_load.py`](benchmark_production_load.py) | Python CLI | High-throughput concurrent load testing and P95/P99 latency distribution analysis. | Yes (Controlled load) |
| [`backup_restore_database.sh`](backup_restore_database.sh) | Bash | Point-in-time PostgreSQL + PostGIS database backup, compression, verification, and restore automation. | Yes (Atomic backup/restore) |

---

## 2. Usage Guide

### 1. Configuration Verification (`verify_production_config.py`)
Run before starting or reloading the FastAPI systemd service:
```bash
python scripts/verify_production_config.py
```
**Checks Performed:**
- Verifies `APP_ENV`, `DEBUG=false`, and `SECRET_KEY` custom configuration.
- Verifies non-wildcard `CORS_ORIGINS`.
- Verifies database pool sizing parameters.
- Performs async connection probe against PostgreSQL and verifies PostGIS spatial extension.
- Masks all sensitive fields in terminal logs.

### 2. Android LAN QR Code Generator (`generate_backend_qr.py`)
Generate an ASCII QR code in your terminal to easily connect the physical Android device:
```bash
python scripts/generate_backend_qr.py
```
Outputs:
- Detected local Wi-Fi / Ethernet LAN IP address.
- Full backend URL (`http://<LAN_IP>:8000/`).
- Scannable ASCII QR code for fast mobile setup.

### 3. Native Deployment Runner (`deploy_native.sh`)
Execute on the native Linux server as the root or `sudo` user:
```bash
sudo ./scripts/deploy_native.sh
```
**Steps Automated:**
1. Pulls latest release tag from git repository.
2. Updates Python virtual environment dependencies (`pip install -r requirements.txt`).
3. Runs database migrations (`alembic upgrade head`).
4. Executes `verify_production_config.py`.
5. Gracefully reloads systemd service (`systemctl restart weathergpt.service`).

### 4. Startup & Latency Benchmark (`benchmark_native.py`)
Measure application cold-start and baseline endpoint latencies:
```bash
python scripts/benchmark_native.py
```
**Metrics Reported:**
- Application construction and cold-start latency (in ms).
- Liveness health probe latency (`/api/v1/health` sub-2ms).
- Readiness dependency probe latency (`/api/v1/ready` sub-2ms).
- 100 sequential requests across Weather, Alerts, and Agricultural decision endpoints.

### 5. High-Throughput Production Load Benchmark (`benchmark_production_load.py`)
```bash
python scripts/benchmark_production_load.py --concurrency 50 --requests 1000
```

### 6. Database Backup & Restore (`backup_restore_database.sh`)
```bash
# Create an atomic compressed backup
./scripts/backup_restore_database.sh backup

# Restore a specific backup file
./scripts/backup_restore_database.sh restore /var/backups/weathergpt/weathergpt_backup_latest.sql.gz
```

---

## 3. Operational Safety Rules
- **No Docker**: All scripts execute directly on host systems without container abstraction.
- **Zero Committed Secrets**: Credentials are read dynamically from `.env` or `/etc/weathergpt/weathergpt.env`.

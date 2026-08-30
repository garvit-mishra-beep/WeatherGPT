# WeatherGPT Operational Scripts

**Directory:** `scripts/`  
**Purpose:** Native Linux deployment helpers, configuration audits, and local latency benchmarking tools.

---

## 1. Overview of Scripts

| Script | Type | Purpose | Safe in Production? |
| :--- | :--- | :--- | :--- |
| [`deploy_native.sh`](deploy_native.sh) | Bash | Non-destructive deployment and upgrade runner for native Linux hosts (Ubuntu/Debian/RHEL). | Yes (Non-destructive) |
| [`verify_production_config.py`](verify_production_config.py) | Python CLI | Audits environment variables, secret masking, PostgreSQL connectivity, and PostGIS extension status. | Yes (Read-only audit) |
| [`benchmark_native.py`](benchmark_native.py) | Python CLI | Measures application cold-start time, health/readiness probe latencies, and executes controlled smoke test requests. | Yes (Read-only benchmarking) |

---

## 2. Usage Guide

### 1. Configuration Verification (`verify_production_config.py`)
Run before starting or reloading the FastAPI systemd service:
```bash
# Using active environment or explicit environment file
python scripts/verify_production_config.py
```
**Checks Performed:**
- Verifies `APP_ENV`, `DEBUG=false`, and `SECRET_KEY` custom configuration.
- Verifies non-wildcard `CORS_ORIGINS`.
- Verifies database pool sizing parameters.
- Performs async connection probe against PostgreSQL and verifies PostGIS spatial extension.
- Masks all sensitive fields in output.

### 2. Native Deployment Runner (`deploy_native.sh`)
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

### 3. Startup & Latency Benchmark (`benchmark_native.py`)
Run to measure application performance baselines:
```bash
python scripts/benchmark_native.py
```
**Metrics Reported:**
- Application construction and cold-start latency (in ms).
- Liveness health probe latency (`/api/v1/health` average and P95).
- Readiness dependency probe latency (`/api/v1/ready` average and P95).
- 100 sequential requests across Weather, Alerts, and Agricultural decision endpoints.

---

## 3. Constraints & Safety Rules
- **No Docker:** Scripts are intended strictly for direct execution in native Python virtual environments and native Linux systemd process managers.
- **Zero Hardcoded Secrets:** All scripts consume credentials dynamically from environment variables or `/etc/weathergpt/weathergpt.env`.

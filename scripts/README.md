# VAYUBODHAK Operational & Automation Scripts

**Directory:** `scripts/`  
**Purpose:** Organized operational tooling, showcase controllers, validation benchmarks, and deployment automation.

---

## Directory Organization

```text
scripts/
├── showcase/
│   └── run_showcase.py              # Canonical scenario controller CLI
├── validation/
│   ├── verify_production_config.py  # Production configuration & security audit
│   ├── benchmark_native.py          # Cold-start and latency smoke testing
│   └── benchmark_production_load.py # Concurrency & P95/P99 latency benchmarks
├── operations/
│   ├── deploy_native.sh             # Linux systemd deployment script
│   └── backup_restore_database.sh   # PostgreSQL + PostGIS backup & restore automation
├── development/
│   ├── ethernet_ollama_bridge.py    # Local LAN LLM bridge
│   ├── generate_backend_qr.py       # Terminal ASCII QR code generator for Android pairing
│   └── START_VAYUBODHAK_DEMO.bat    # Windows local staging launcher
├── run_showcase.py                  # Forwarding wrapper delegating to showcase/run_showcase.py
└── README.md
```

---

## 1. Showcase Scenario Controller

Run deterministic video showcase steps:

```bash
# Reset state to clean baseline
python scripts/showcase/run_showcase.py reset

# Step 0: Baseline (Nominal rain 3.0mm -> Revision 1)
python scripts/showcase/run_showcase.py start

# Step 1: Precipitation escalation (88.5mm rain -> Revision 2)
python scripts/showcase/run_showcase.py next

# Step 2: Statutory alert escalation (Red Warning -> Revision 3)
python scripts/showcase/run_showcase.py next

# Step 3: Offline mode simulation
python scripts/showcase/run_showcase.py next

# Step 4: Network recovery & sync reconciliation
python scripts/showcase/run_showcase.py next
```

*(Note: `python scripts/run_showcase.py` remains supported as a legacy delegating forwarder).*

---

## 2. Configuration & Validation

### Configuration Audit
```bash
python scripts/validation/verify_production_config.py
```
- Verifies `APP_ENV`, `DEBUG=false`, and `SECRET_KEY` custom configuration.
- Verifies non-wildcard `CORS_ORIGINS`.
- Verifies database pool sizing parameters.
- Probes PostgreSQL connectivity and PostGIS extension status.

### Performance Benchmarking
```bash
python scripts/validation/benchmark_native.py
python scripts/validation/benchmark_production_load.py
```

---

## 3. Operations & Deployment

### Linux Deployment
```bash
bash scripts/operations/deploy_native.sh
```

### Database Backup & Restore
```bash
bash scripts/operations/backup_restore_database.sh
```

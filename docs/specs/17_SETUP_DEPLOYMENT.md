# WeatherGPT — Setup, Installation & Deployment Guide

**Document:** `17_SETUP_DEPLOYMENT.md`  
**Status:** Approved Technical Guide  
**Primary PRD Reference:** [docs/01_PRD.md](01_PRD.md)  
**Related Specs:** [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md), [06_API_CONTRACT.md](06_API_CONTRACT.md), [10_DATABASE_SCHEMA.md](10_DATABASE_SCHEMA.md)

---

## 1. Repository Structure

```text
WeatherGPT/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI Application Entrypoint
│   ├── config.py                # Pydantic Settings & Environment Loader
│   ├── api/                     # REST API Routers
│   │   ├── v1/
│   │   │   ├── chat.py          # Conversational Chat & Disambiguation Endpoints
│   │   │   ├── weather.py       # Weather Observation & Alert Endpoints
│   │   │   ├── farmer.py        # Agricultural & Spray Window Endpoints
│   │   │   ├── research.py      # Statistical & Trend Endpoints
│   │   │   └── gis.py           # Spatial Intersection & Exposure Endpoints
│   ├── router/                  # Auto Router & Domain Intent Classifiers
│   │   ├── engine.py
│   │   └── prompts.py
│   ├── brains/                  # Domain Brain Implementations
│   │   ├── general.py
│   │   ├── farmer.py
│   │   ├── researcher.py
│   │   └── analyst.py
│   ├── tools/                   # Tool Gateway & Implementations
│   │   ├── registry.py
│   │   ├── weather_tools.py
│   │   ├── ag_tools.py
│   │   ├── stats_tools.py
│   │   └── gis_tools.py
│   ├── adapters/                # Meteorological Data Providers
│   │   ├── imd.py
│   │   ├── gfs.py
│   │   └── open_meteo.py
│   ├── analytics/               # Deterministic Math Engines
│   │   ├── fao56.py             # FAO-56 Penman-Monteith ET0 Engine
│   │   ├── stats.py             # Mann-Kendall & Sen's Slope
│   │   └── risk.py              # Hazard-Exposure Matrix
│   ├── db/                      # Database Models & Migrations
│   │   ├── session.py
│   │   ├── models.py
│   │   └── migrations/
│   └── gis/                     # PostGIS Spatial Handlers
├── data/
│   ├── spatial/                 # District & State Shapefiles / GeoJSON
│   └── crops/                   # Crop Catalog & Stage Coefficients JSON
├── docs/                        # Complete Technical Documentation Suite
├── tests/                       # Comprehensive pytest Test Suite
├── docker-compose.yml           # Local Single-Machine Development Stack
├── Dockerfile                   # FastAPI Container Image
├── requirements.txt             # Python Dependencies
└── .env.example                 # Environment Variable Template
```

---

## 2. Prerequisites & Environment Requirements

* **Python:** 3.11 or 3.12
* **Database:** PostgreSQL 16+ with PostGIS 3.4+ extension
* **In-Memory Cache:** Redis 7.0+
* **System Libraries (for Geospatial & GRIB2 parsing):** `libgdal-dev`, `libgeos-dev`, `libproj-dev`, `libeccodes-dev`
* **LLM Engine (Inference Node):** vLLM 0.5+ / Ollama 0.3+ running Llama-3-8B-Instruct or Qwen-2.5-14B/72B

---

## 3. Environment Configuration (`.env.example`)

```ini
# --- Application Settings ---
ENVIRONMENT=development
APP_PORT=8000
DEBUG=true
SECRET_KEY=change_this_to_a_secure_random_string_in_production

# --- Database & Cache ---
DATABASE_URL=postgresql://postgres:postgres_dev_password@localhost:5432/weathergpt
REDIS_URL=redis://localhost:6379/0

# --- LLM Inference Host (Points to Laptop 1 in Two-Laptop Topology) ---
LLM_BASE_URL=http://192.168.1.101:8001/v1
LLM_MODEL_NAME=meta-llama/Meta-Llama-3-8B-Instruct
LLM_API_KEY=not_required_for_local_vllm
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=1024

# --- Meteorological Ingestion & APIs ---
IMD_CAP_FEED_URL=https://sachet.ndma.gov.in/cap_feed/rss
GFS_AWS_S3_BUCKET=noaa-gfs-bdp-pds
OPEN_METEO_BASE_URL=https://api.open-meteo.com/v1
```

---

## 4. Step-by-Step Setup for Two-Laptop Development Topology

### 4.1 Laptop 1: LLM Inference Node Setup
*Hardware Target: GPU Machine (e.g., RTX 4080/4090 or Apple Silicon M-Series)*

1. **Assign Static LAN IP:** Configure machine network IP to `192.168.1.101`.
2. **Launch vLLM Server:**
   ```bash
   # Install vLLM
   pip install vllm

   # Start OpenAI-compatible server exposing port 8001 to LAN
   python -m vllm.entrypoints.openai.api_server \
       --model meta-llama/Meta-Llama-3-8B-Instruct \
       --host 0.0.0.0 \
       --port 8001 \
       --gpu-memory-utilization 0.90 \
       --max-model-len 4096
   ```
3. **Verify Connectivity from Terminal:**
   ```bash
   curl http://localhost:8001/v1/models
   ```

#### 4.1.1 Alternative: Remote Ollama Host (e.g. Laptop UJJWAL with Gemma 4:e2b)
When utilizing a second laptop on the local network running Ollama:
- **Host / DNS Name:** `UJJWAL` (preferred over dynamic DHCP IPs)
- **Port:** `11434`
- **Model:** `gemma4:e2b`
- **Connectivity Check:**
  ```bash
  curl http://UJJWAL:11434/api/tags
  ```
- **Backend Configuration (`.env`):**
  ```env
  LLM_PROVIDER_TYPE=ollama
  OLLAMA_ENABLED=true
  OLLAMA_BASE_URL=http://UJJWAL:11434
  OLLAMA_MODEL=gemma4:e2b
  OLLAMA_TIMEOUT_SECONDS=60.0
  ```

---

### 4.2 Laptop 2: Core Services & Application Setup
*Hardware Target: Multi-core CPU & High-RAM Machine*

1. **Assign Static LAN IP:** Configure machine network IP to `192.168.1.100`.
2. **Install PostGIS & Redis:**
   ```bash
   # Ubuntu / Debian
   sudo apt update && sudo apt install -y postgresql-16 postgresql-16-postgis-3 redis-server gdal-bin libeccodes-dev

   # Create Database with PostGIS extension
   sudo -u postgres psql -c "CREATE DATABASE weathergpt;"
   sudo -u postgres psql -d weathergpt -c "CREATE EXTENSION IF NOT EXISTS postgis;"
   ```
3. **Setup Python Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. **Run Migrations & Seed GIS Spatial Data:**
   ```bash
   # Apply schema migrations
   alembic upgrade head

   # Seed Indian administrative boundaries and crop catalog
   python scripts/seed_spatial_boundaries.py --geojson data/spatial/india_districts.geojson
   python scripts/seed_crop_catalog.py --json data/crops/icar_crop_stages.json
   ```
5. **Verify Connection to Laptop 1 Inference Node:**
   ```bash
   curl http://192.168.1.101:8001/v1/models
   ```
6. **Start FastAPI Application Server:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## 5. Single-Machine Docker Compose Stack

For developers running all components on a single machine:

```yaml
version: '3.8'

services:
  db:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: weathergpt
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7.2-alpine
    ports:
      - "6379:6379"

  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:dev_password@db:5432/weathergpt
      REDIS_URL: redis://redis:6379/0
      LLM_BASE_URL: http://host.docker.internal:8001/v1
    depends_on:
      - db
      - redis

volumes:
  pgdata:
```

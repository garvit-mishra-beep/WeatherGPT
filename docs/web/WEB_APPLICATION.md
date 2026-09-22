# VAYUBODHAK Web Application Guide

## 1. Introduction

The **VAYUBODHAK Web Application** provides a responsive, desktop-optimized frontend for the VAYUBODHAK Disaster Intelligence System. Built with **Next.js 15, React 19, and TypeScript**, it delivers exact visual and architectural parity with the existing Android mobile application while taking full advantage of modern desktop displays ($1440 \times 900$ and $1920 \times 1080$).

The web frontend operates as a peer client alongside the Android application, consuming the exact same FastAPI backend services.

---

## 2. Quick Start & Local Development

### Prerequisites
* **Node.js**: v18.18+ or v20+ (Verified on Node v26.1.0)
* **Python Backend**: Running on `http://127.0.0.1:8000`

### Step-by-Step Setup

1. **Start the FastAPI Backend:**
   ```powershell
   # From repository root:
   .\.venv\Scripts\Activate.ps1
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

2. **Run the Web Application:**
   ```powershell
   cd web
   npm install
   npm run dev
   ```

3. **Access the Web Dashboard:**
   Open your browser and navigate to:
   ```text
   http://localhost:3000
   ```
   *(Next.js automatically rewrites `/api/backend/*` to `http://127.0.0.1:8000/api/v1/*` to eliminate CORS hurdles).*

4. **Run Web Tests:**
   ```powershell
   cd web
   npm test
   ```

5. **Build for Production:**
   ```powershell
   cd web
   npm run build
   npm run start
   ```

---

## 3. Route Guide & Capabilities

### 3.1 Overview (`/overview`)
The primary situational awareness cockpit. Adapts the Android Home Screen to a multi-column desktop canvas:
* **Current Weather Observation Card**: Temperature, relative humidity, wind speed, precipitation, and provider provenance.
* **Hazard Card**: Intensity evaluation, active hazard rules, and physical hazard scores.
* **Risk Card**: Authoritative 3-factor composite risk index ($0.50H + 0.30E + 0.20V$).
* **Nirnay Card**: Prominent operational verdict banner (`GO`, `PROCEED_WITH_CAUTION`, `POSTPONE`, `NO_GO`, `MONITOR`), recommended operational action, action window feasibility, and expandable verification ledger.
* **Seven-Stage Pipeline**: Clickable visual pipeline showing exact backend evaluations at each stage.
* **Impact Matrix**: Disruption breakdown across Agriculture, Critical Infrastructure, and Population.

### 3.2 Four Brains (`/intelligence/[brain]`)
Unified intelligence persona views sharing the same evidence foundation:
* **Analyst Brain (`/intelligence/analyst`)**: Detailed mathematical decomposition, hazard indices, exposure fragility models, and vulnerability factors.
* **Farmer Brain (`/intelligence/farmer`)**: Agricultural advisory, crop submergence risk, spraying/harvesting action windows, and soil saturation alerts.
* **Researcher Brain (`/intelligence/researcher`)**: Audit-grade provenance, observation timestamps, sensor telemetry, and cryptographic hash verification.
* **General Brain (`/intelligence/general`)**: Public situational awareness, plain-language guidance, emergency instructions, and offline safety notices.

### 3.3 Evidence Foundation (`/evidence`)
Demonstrates that VAYUBODHAK is strictly **evidence-first**:
* Cards display data source, statutory authority tier, observation timestamp, parameter value, confidence rating, and cryptographic signature.
* Visual filtering by statutory authority: IMD, CWC, NDMA, ECMWF, and Sensor Telemetry.

### 3.4 Nirnay Decision Center (`/nirnay`)
Comprehensive decision engine ledger:
* Full operational verdict banner with severity badge.
* Action Window scanner detailing candidate hours, rejection reasons, and optimal operation windows.
* Verified Rule Ledger listing each evaluated statutory safety threshold (`PASSED`, `FAILED`, `MARGINAL`).
* Revision History timeline showing decision evolution as operational events arrive.

### 3.5 Alerts & Events (`/alerts`)
Real-time operational notifications stream:
* Categorized by priority: `OFFICIAL_WARNING`, `DECISION_CHANGE`, `HAZARD_ADVISORY`, `INFO`.
* Operational event replay showing raw event payloads, sequences, and change detection triggers.

### 3.6 System & Resilience Status (`/system-status`)
Comprehensive resilience cockpit matching Android's `SystemStatusScreen`:
* Overall System Operational State (`FULL_OPERATIONAL`, `DEGRADED_DATA`, `OFFLINE`, `RECOVERING`, `UNAVAILABLE`).
* Freshness Safety Card detailing offline data policies and last-verified timestamp.
* Official Warning Authority status badges.
* Independent LLM Status panel with failure decoupling notice.
* Telemetry feeds catalog and health telemetry.
* Manual "Force Sync Now" trigger.

### 3.7 Meteorological Map (`/map`)
GIS and radar map matching Android's `MapScreen`:
* Leaflet-powered GIS engine with OpenStreetMap and Satellite base layers.
* Live animated rain radar overlay powered by RainViewer API.
* Quick location chips (Gwalior, New Delhi, Bhopal, Indore, Jabalpur, Mumbai, Jaipur, Lucknow).
* Address and coordinate geocoding search pill.
* User geolocation locator button.

---

## 4. Controlled Showcase Runner

The web interface integrates the **ShowcaseBar** controller pinned to the top of the application:
* **START**: Initiates the controlled scenario from baseline ($t=0$).
* **NEXT**: Advances step-by-step through:
  1. *Baseline*: Moderate weather, MONITOR verdict, LOW severity.
  2. *Rain Escalation*: Precipitation surge, Hazard recalculation, PROCEED_WITH_CAUTION.
  3. *Warning Escalation*: Statutory warning bulletin received, POSTPONE verdict, HIGH severity.
  4. *Nirnay Revision*: Full threshold breach, NO_GO verdict, CRITICAL severity, broadcast notification.
* **RESET**: Returns system to nominal live monitoring.
* **Attribution Invariant**: All controlled scenario steps are strictly attributed as `CONTROLLED_SCENARIO` and never displayed as live statutory data.

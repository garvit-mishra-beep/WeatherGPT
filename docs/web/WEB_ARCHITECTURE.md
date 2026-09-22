# VAYUBODHAK Web Application Architecture

## 1. Executive Summary & Philosophy

The **VAYUBODHAK Web Application** (`web/`) is an enterprise-grade presentation layer built with **Next.js 15, React 19, and TypeScript**. It connects directly to the existing **VAYUBODHAK FastAPI backend** (`http://127.0.0.1:8000/api/v1/`), preserving the exact analytical engines, decision matrices, and resilience guarantees of the platform.

### Core Architectural Invariant
> **The Web UI is a new presentation surface, NOT a second disaster engine.**
>
> All analytical calculations, risk decompositions ($0.50H + 0.30E + 0.20V$), hazard rules, and Nirnay verdicts originate exclusively from the authoritative Python backend. The web application strictly consumes backend-generated state.

```text
                           VAYUBODHAK BACKEND
                        (FastAPI / Python Engines)
                                     │
                 ┌───────────────────┴───────────────────┐
                 ↓                                       ↓
           Android Client                           Web Client
        (Jetpack Compose Mobile)               (Next.js 15 Desktop/Web)
                 │                                       │
                 └───────────────────┬───────────────────┘
                                     ↓
                          SAME PRODUCT IDENTITY
                          SAME EVIDENCE CHAIN
                          SAME RISK ENGINE
                          SAME NIRNAY VERDICT
```

---

## 2. Dual-Client Visual & Functional Parity

| Dimension | Android Application (`android/`) | Web Application (`web/`) |
| :--- | :--- | :--- |
| **Design Token Source** | `Color.kt` / `Theme.kt` | `styles/globals.css` CSS Tokens |
| **Primary Brand Color** | Forest Emerald (`#1B5E20`) | `--vayu-primary: #1B5E20` |
| **Primary Container** | Mint Tint (`#E8F5E9`) | `--vayu-primary-container: #E8F5E9` |
| **Secondary Accent** | Deep Teal (`#00796B`) | `--vayu-secondary: #00796B` |
| **Canvas Background** | Ultra-soft Sage Canvas (`#F8FAF8`) | `--vayu-background: #F8FAF8` |
| **Severity Tiers** | Green (`#16A34A`), Yellow (`#CA8A04`), Orange (`#EA580C`), Red (`#DC2626`) | Identical hex codes & semantics |
| **Core Components** | `NirnayCard.kt`, `SystemStatusIndicator.kt` | `NirnayCard.tsx`, `SystemStatusIndicator.tsx` |
| **Map Engine** | `assets/weather_map.html` in Android WebView | `public/weather_map.html` with PostMessage bridge |
| **Synchronization** | `OperationalSyncManager.kt` cursor polling | `useOperationalState.ts` cursor polling |

---

## 3. Core Intelligence Pipeline

Every screen and card in the web frontend strictly maps to the authoritative seven-stage disaster pipeline:

```text
Evidence  ──>  Hazard  ──>  Exposure  ──>  Vulnerability  ──>  Risk  ──>  Potential Impact  ──>  Nirnay
(Sources)     (Physics)    (Assets)       (Fragility)        (Matrix)      (Sectoral Loss)       (Verdict)
```

1. **Evidence Stage (`/evidence`):** Cryptographically verifiable provenance, authority tiers (Statutory IMD/CWC/NDMA > Verified > Supporting), observation timestamps, and SHA-256 signatures.
2. **Hazard Stage:** Rainfall rates, wind speeds, flood gauge levels evaluated against statutory thresholds.
3. **Exposure Stage:** District-level infrastructure (hospitals, schools, road networks, agricultural acreage).
4. **Vulnerability Stage:** Structural fragility, socioeconomic exposure factors, drainage adequacy.
5. **Risk Stage:** Weighted composite risk index:
   $$\text{Composite Risk} = 0.50 \cdot H + 0.30 \cdot E + 0.20 \cdot V$$
6. **Potential Impact Stage:** Quantitative disruption estimates (population at risk, crop submersion hectares).
7. **Nirnay Decision Stage (`/nirnay`):** Definitive operational verdict (`GO`, `PROCEED_WITH_CAUTION`, `POSTPONE`, `NO_GO`, `MONITOR`) backed by a non-repudiable audit ledger.

---

## 4. Resilience & Decoupled LLM Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                      VAYUBODHAK RESILIENCE LAYER                       │
├──────────────────────────────────────┬─────────────────────────────────┤
│    DETERMINISTIC ASSESSMENTS         │    INFORMATIONAL AI LAYER       │
│    (Authoritative & Uninterruptible) │    (Decoupled & Optional)       │
├──────────────────────────────────────┼─────────────────────────────────┤
│ • Rule Engine (Python)               │ • LLM Narrative Generation      │
│ • Risk Decompositions                │ • Natural Language Query        │
│ • Potential Impact Calculations      │ • Multilingual Summaries        │
│ • Nirnay Verdicts                    │                                 │
│                                      │ If LLM fails:                   │
│ ALWAYS ACTIVE (Online, Cached,       │ System displays:                │
│ or Offline)                          │ "AI explanation temporarily     │
│                                      │ unavailable. Verified disaster  │
│                                      │ assessment remains available."  │
└──────────────────────────────────────┴─────────────────────────────────┘
```

### System Operational States
* `FULL_OPERATIONAL`: All primary and secondary feeds live, low latency.
* `DEGRADED_DATA`: Secondary feeds unreachable; primary statutory bounds enforce conservative fallbacks.
* `OFFLINE`: Network unreachable. UI displays cryptographically sealed cached state labeled `CACHED`.
* `RECOVERING`: Network restored; replaying missing operational events via cursor synchronization.
* `UNAVAILABLE`: Neither live nor cached telemetry accessible.

---

## 5. Web Directory Structure

```text
web/
├── app/
│   ├── layout.tsx              # Brand layout, persistent Sidebar & ShowcaseBar
│   ├── page.tsx                # Client redirect to /overview
│   ├── overview/               # Full desktop adaptation of Android Home Screen
│   ├── intelligence/[brain]/   # Dedicated Four Brains views (Analyst, Farmer, Researcher, General)
│   ├── evidence/               # Evidence foundation with audit provenance
│   ├── nirnay/                 # Decision ledger & revision history
│   ├── alerts/                 # Operational notifications & event log
│   ├── system-status/          # Feed health, resilience states, LLM status
│   └── map/                    # Meteorological radar & exposure GIS map
│
├── components/
│   ├── dashboard/              # WeatherCard, HazardCard, RiskCard, ImpactCard, Pipeline
│   ├── nirnay/                 # NirnayCard with rule verification ledger
│   ├── evidence/               # EvidenceCard with hash signatures
│   ├── intelligence/           # BrainSelector with metadata
│   ├── resilience/             # SystemStatusIndicator & LLMStatusNotice
│   ├── showcase/               # ShowcaseBar (Start / Next / Reset controls)
│   └── layout/                 # Header & Sidebar navigation
│
├── hooks/
│   └── useOperationalState.ts  # Cursor synchronization & offline cache state machine
│
├── lib/
│   └── api/
│       ├── client.ts           # Resilient fetch client with localStorage cache
│       ├── sync.ts             # Incremental operational sync wrapper
│       ├── decisions.ts        # Nirnay decision fetching
│       ├── weather.ts          # Current observations & forecasts
│       ├── analyst.ts          # Risk matrix & engine wrappers
│       ├── sources.ts          # Telemetry feed catalog & health
│       └── showcase.ts         # Showcase runner controls
│
├── public/
│   └── weather_map.html        # Leaflet radar & GIS mapping engine
│
├── styles/
│   └── globals.css             # Android-parity CSS design tokens
│
└── tests/
    └── web_components.test.mjs # Automated unit & invariant test suite
```

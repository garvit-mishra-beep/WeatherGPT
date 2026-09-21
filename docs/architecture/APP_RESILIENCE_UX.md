# VAYUBODHAK — Android Application Resilience & Failure-Aware UX

## 1. Core Architectural Principle

VAYUBODHAK adheres to two non-negotiable operational principles:

1. **Data Freshness Integrity**: Data availability can degrade without pretending that the system has fresh information. Never hide data freshness or source failure. Never make cached or stale information appear live.
2. **LLM Decoupling**: LLM availability is strictly decoupled and independent from deterministic disaster intelligence. Deterministic hazard, exposure, vulnerability, risk, potential impact, and NirnayCard generation proceed unaffected even if LLM connectivity is completely unavailable.

```
                    ┌─────────────────────────┐
                    │  LIVE OPERATIONAL DATA  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │     EVIDENCE LAYER      │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  DETERMINISTIC ENGINES  │
                    │ (Hazard/Exposure/Risk)  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │       NIRNAY CARD       │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │       ANDROID APP       │
                    └────────────┬────────────┘
                                 ▲
                                 │ (Offline / Cached state)
                    ┌────────────┴────────────┐
                    │    ROOM LOCAL STORAGE   │
                    └─────────────────────────┘

      ═════════════════ SEPARATION LINE ═════════════════

                    ┌─────────────────────────┐
                    │       NIRNAY CARD       │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │       LLM GATEWAY       │
                    └────────────┬────────────┘
                                 │ (Optional)
                                 ▼
                    ┌─────────────────────────┐
                    │ EXPLANATION/TRANSLATION │
                    └─────────────────────────┘
```

---

## 2. Canonical State Models

### 2.1 SystemOperationalState
Exposes the holistic operational posture of the client application:

* `FULL_OPERATIONAL`: All essential data sources are reporting live telemetric data. Full deterministic & advisory capabilities active.
* `DEGRADED_DATA`: One or more operational data feeds are unavailable or currently operating via configured secondary fallback adapters.
* `OFFLINE`: Complete loss of physical or cellular network connectivity. App serves strictly verified cached data with explicit timestamps.
* `RECOVERING`: Connectivity has been restored; synchronization pipeline is validating and fetching new differential deltas.
* `UNAVAILABLE`: Essential evidence feeds have lapsed or no verified cached baseline is present for current spatiotemporal coordinates.

### 2.2 SourceOperationalStatus
Individual status for each underlying data source:

* `LIVE`: Data fetched successfully within the active freshness validity window directly from authoritative primary provider.
* `CACHED`: Primary fetch failed or offline; data rendered is sourced from verified local Room persistent storage with recorded observation/verification timestamp.
* `FALLBACK`: Primary provider failed; data currently retrieved from pre-configured secondary supporting provider.
* `STALE`: Data timestamp exceeds maximum permissible operational validity window; displayed with prominent warning banner.
* `UNAVAILABLE`: Neither primary, fallback, nor cached data is accessible.
* `HISTORICAL`: Long-term reference or census/topographic baseline data.

### 2.3 LlmStatus
Independent state tracking for GenAI conversational/explanation layer:

* `LLM_AVAILABLE`: Remote LLM endpoint responsive and functioning within latency thresholds.
* `LLM_UNAVAILABLE`: Remote LLM endpoint failed (5xx, timeout, quota). AI explanation banner alerts user that deterministic assessments remain 100% active.
* `LLM_LOCAL_AVAILABLE`: On-device or local edge fallback inference active.
* `LLM_RECOVERING`: Re-establishing model inference session.

### 2.4 OfficialWarningStatus
Dedicated state for statutory government warnings (e.g., IMD, NDMA, CWC):

* `AVAILABLE`: Active statutory warning received and verified.
* `UPDATED`: Warning revised with updated severity or polygon.
* `EXPIRED`: Warning validity window has lapsed.
* `CANCELLED`: Warning officially rescinded by authority.
* `UNAVAILABLE`: Official source unreachable. (Crucial rule: **No synthetic or third-party fallback may be presented as official warning**).

---

## 3. UI Components & Interaction

### 3.1 Compact System Status Indicator (`SystemStatusIndicator.kt`)
- Placed directly on the primary home screen dashboard underneath the header.
- Uses multi-attribute accessibility: **Text + Icon + Color + Semantic Description** (never color alone).
- Clickable banner immediately navigates the operator to the full `SystemStatusScreen`.

| State | Badge Text | Subtitle | Icon |
|---|---|---|---|
| `FULL_OPERATIONAL` | `SYSTEM OPERATIONAL` | `Live data available` | CheckCircle |
| `DEGRADED_DATA` | `DEGRADED MODE` | `Some live data unavailable` | Warning |
| `OFFLINE` | `OFFLINE MODE` | `Showing last verified information` | CloudOff |
| `RECOVERING` | `RECOVERING` | `Synchronizing latest information` | Refresh (Spinning) |
| `UNAVAILABLE` | `DATA UNAVAILABLE` | `No verified current information available` | Info |

### 3.2 AI Assistant Degradation Banner
When `llmStatus == LlmStatus.LLM_UNAVAILABLE`, an accessible amber notice displays inside conversation screens:
> *"AI explanation temporarily unavailable. Verified disaster assessment remains available."*

### 3.3 NirnayCard Resilience Indicator (`NirnayCard.kt`)
Every decision card explicitly reveals evidence freshness directly adjacent to the Risk/Action recommendation:
- **Evidence Status**: `VERIFIED` (Green), `CACHED` (Orange), `STALE` (Amber), `FALLBACK` (Blue), `UNAVAILABLE` (Red).
- **Assessment Timestamp**:
  - Live: `Assessment updated: 10:41 AM`
  - Stale/Cached: `Assessment based on last verified information: 10:32 AM`
- **Safety Message** (When stale/cached):
  > *"This information was last verified at 10:32 AM. Live data is currently unavailable."*

### 3.4 Detailed System Status Screen (`SystemStatusScreen.kt`)
Provides transparent, operator-grade visibility into all data pipelines:
1. **Overall Status Card**: Badge, headline, description, and last verified timestamp.
2. **Operational Safety Notice**: Clear guidance clarifying that live data is degraded and cached records are being utilized.
3. **Official Warning Section**: Authoritative statutory alert status with dedicated disclaimer.
4. **AI Assistant Section**: Independent LLM availability status.
5. **Source Health Breakdown**: Itemized listing of each source (Weather, Official Warning, GIS, Population) showing status badge, last successful fetch, and provider fallback notes.
6. **Retry & Synchronization Action**: One-tap "Retry now" triggering immediate ping and synchronization.

---

## 4. Offline & Recovery Workflow

1. **Connectivity Loss**:
   - `NetworkMonitor` detects network interface drops.
   - `SystemResilienceManager.onDeviceWentOffline()` triggers.
   - `systemState` transitions to `OFFLINE`.
   - UI switches to cached mode, preserving and rendering verification timestamps for all stored records.
2. **Connectivity Restored**:
   - `NetworkMonitor` detects network interface online.
   - `SystemResilienceManager.onConnectivityRestored()` triggers.
   - `systemState` transitions to `RECOVERING`.
   - Incremental differential synchronization pulls latest operational records.
   - Upon successful synchronization, `completeSynchronization()` transitions `systemState` to `FULL_OPERATIONAL` (or `DEGRADED_DATA` if a source remains down).

---

## 5. Four-Brain Compatibility

Resilience states are scoped to the active cognitive context:
- **General Brain**: Alerts on regional hazard data degradation.
- **Farmer Brain**: Displays: *"AI explanation unavailable. Agricultural verified data available."*
- **Researcher Brain**: Exposes full provenance metadata and revision counters.
- **Analyst Brain**: Highlights source fallback disclaimers and multi-source variance.

---

## 6. Verification and Test Suite

The resilience layer is verified by dedicated automated unit test suites:
- `SystemResilienceManagerTest.kt`: Validates all 10 state transition scenarios including network drops, recovery, LLM failures, fallback disclaimers, and manual retries.
- `NirnayCardResilienceTest.kt`: Validates evidence freshness badge generation, safety banners, and timestamp formats.
- `SystemStatusUiStateTest.kt`: Validates visual attribute mapping, accessibility labeling, and disclaimer generation.

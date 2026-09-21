# VAYUBODHAK — VIDEO SHOWCASE SCENARIO MANUAL

## Operational Demonstration Architecture: Controlled Inputs + Real Analytical Pipeline

---

## 1. Executive Summary

This scenario specification guides the repeatable, video-ready recording of **VAYUBODHAK**. The application demonstrates real operational decision intelligence under dynamic meteorological escalation and degraded network conditions.

The system adheres strictly to the **Data-Truth Principle**:
> **Controlled demo data is utilized as INPUT; all analytical calculations (Hazard, Exposure, Vulnerability, Risk, Impact, Decision, Revision, Notification, and Sync) are 100% REAL OUTPUTS.**

At no point does the application present hardcoded scores, fake animations, or simulate outputs. No user-facing screen exposes debug labels such as "Demo Mode", "Mock Mode", or "Test Build".

---

## 2. Demonstration Location

| Attribute | Specification | Operational Grounding |
| :--- | :--- | :--- |
| **District** | **Gwalior District** | Real Indian administrative division in Madhya Pradesh |
| **Coordinates** | Latitude: `26.2183° N`, Longitude: `78.1828° E` | Central Gwalior synoptic coordinate |
| **Elevation** | 197.0 meters AMSL | Chambal-Gird alluvial plains |
| **Major Transport** | National Highway 44 (North-South), State Highway 19 | Critical connectivity corridors |
| **Healthcare Hub** | Jaya Arogya Hospital (1,200 beds, 85 ICUs) | Major regional tertiary hospital |
| **Agricultural Base** | 184,500 hectares (Soybean, Mustard, Wheat) | Vulnerable anthesis/flowering crop stages |

---

## 3. End-to-End Scenario Timeline

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             SHOWCASE TIMELINE FLOW                               │
├──────────────┬─────────────────────────────┬───────────────────┬─────────────────┤
│ Step Index   │ Scenario Step Name          │ Operational Event │ Key Transition  │
├──────────────┼─────────────────────────────┼───────────────────┼─────────────────┤
│ **Step 0**   │ BASELINE_NOMINAL            │ EVT-SHOWCASE-001  │ Revision 1      │
│              │ Light shower (3.0mm), 28.5°C│ Weather Update    │ Verdict: MONITOR│
├──────────────┼─────────────────────────────┼───────────────────┼─────────────────┤
│ **Step 1**   │ PRECIPITATION_ESCALATION    │ EVT-SHOWCASE-002  │ Revision 2      │
│              │ Heavy rain (88.5mm), 42km/h │ Delta > 64.5mm    │ Verdict: CAUTION│
├──────────────┼─────────────────────────────┼───────────────────┼─────────────────┤
│ **Step 2**   │ OFFICIAL_WARNING_ESCALATION │ EVT-SHOWCASE-003  │ Revision 3      │
│              │ Statutory Red Warning (IMD) │ E0 Authority Alert│ Verdict: POSTPONE│
├──────────────┼─────────────────────────────┼───────────────────┼─────────────────┤
│ **Step 3**   │ OFFLINE_RESILIENCE          │ Network severed   │ Cached State    │
│              │ Airplane mode / disconnect  │ Room preservation │ Status: OFFLINE │
├──────────────┼─────────────────────────────┼───────────────────┼─────────────────┤
│ **Step 4**   │ RECOVERY_RECONCILIATION     │ Network restored  │ Incremental     │
│              │ Reconnect to backend        │ Cursor sync       │ Latest Revision │
└──────────────┴─────────────────────────────┴───────────────────┴─────────────────┘
```

---

## 4. Stage-by-Stage Input Values & Analytical Responses

### Step 0: Baseline Nominal State
* **Input Dataset**: `data/showcase/weather_initial.json`
* **Precipitation**: `3.0 mm`
* **Temperature / Wind**: `28.5 °C`, `12.5 km/h`
* **Real Pipeline Processing**:
  * Evidence Record created with cryptographic SHA-256 seal.
  * Operational Event `EVT-SHOWCASE-001` (Sequence 1) ingested.
  * Deterministic Hazard engine computes `HEAVY_RAINFALL = NOMINAL`.
  * Risk Score: `0.08` (Category: `LOW`).
  * Potential Impact: Minimal infrastructure disruption.
  * Decision Engine generates `NirnayCard`: **Verdict = MONITOR**, **Severity = LOW**.
  * DecisionRevision 1 persisted (`REV-SHOWCASE-001`).

### Step 1: Precipitation Escalation
* **Input Dataset**: `data/showcase/weather_rain_increase.json`
* **Precipitation**: `88.5 mm` (Delta: `+85.5 mm`, crossing both `2.5 mm` rain and `64.5 mm` heavy rain thresholds).
* **Wind / Gusts**: `42.0 km/h` / `65.0 km/h`.
* **Real Pipeline Processing**:
  * Operational Event `EVT-SHOWCASE-002` (Sequence 2) ingested.
  * `ChangeDetector` evaluates delta: triggers `PRECIPITATION_ESCALATION` (`is_significant = True`).
  * Selective Recalculation:
    * **Reused**: `EXPOSURE`, `VULNERABILITY` (zero unnecessary compute).
    * **Recomputed**: `HAZARD`, `RISK`, `IMPACT`, `DECISION`.
  * Risk Score elevates to Moderate; Road segment `ROAD-NH-44-GWL` inundation risk identified.
  * Decision Engine updates `NirnayCard`: **Verdict = PROCEED_WITH_CAUTION**, **Severity = MODERATE**.
  * Action: *"Precipitation escalation detected (88.5mm). Clear drainage channels and secure low-lying assets."*
  * DecisionRevision 2 created.
  * Real notification emitted: `Decision Update [PROCEED_WITH_CAUTION]: Gwalior District`.

### Step 2: Official Warning Escalation
* **Input Dataset**: `data/showcase/warning_update.json`
* **Authority**: India Meteorological Department (IMD, Statutory E0 Authority).
* **Warning Code**: Red Warning (`CAP 1.2` Alert Code).
* **Headline**: *"Red Warning: Extreme Localized Precipitation & Flash Flooding"*.
* **Real Pipeline Processing**:
  * Operational Event `EVT-SHOWCASE-003` (Sequence 3) ingested.
  * Rule `DEC-RULE-OFFICIAL-WARN-001` activates.
  * Decision Engine updates `NirnayCard`: **Verdict = POSTPONE**, **Severity = HIGH**.
  * Recommended Action: *"Halt outdoor operations. Comply with official IMD Red Warning advisory."*
  * DecisionRevision 3 created.
  * Priority Notification dispatched: `[OFFICIAL ALERT] RED Warning: Gwalior District`.

### Step 3: Offline Resilience Scene
* **Action**: Disconnect mobile device / disable network connectivity.
* **Client Behavior**:
  * `SystemResilienceManager` detects connection failure and transitions to `OFFLINE_CACHE`.
  * Mobile UI renders badge: `OFFLINE VERIFIED` / `Controlled scenario`.
  * Screen continues displaying last verified state (Revision 3, Sequence 3, POSTPONE verdict).
  * Last verified timestamp is preserved; zero crashes, zero blank screens, zero fake "live" claims.

### Step 4: Recovery Scene
* **Action**: Reconnect mobile network.
* **Client Behavior**:
  * `SystemResilienceManager` transitions state to `RECOVERING`.
  * `OperationalSyncManager.onConnectivityRestored()` issues incremental GET `/api/v1/sync/operational-state?cursor_seq=1`.
  * Reconciles missing events and confirms latest revision without downloading redundant historical data.
  * Status returns to full operational mode.

---

## 5. Scripted Operator Recording Instructions

### Pre-Flight Setup
1. Start backend server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
2. Reset scenario state to clean baseline:
   ```bash
   python scripts/run_showcase.py reset
   ```

### Scene 1: Baseline Launch (0:00 - 0:45)
* Run: `python scripts/run_showcase.py start`
* Show Android App opening on Gwalior home screen.
* Point out: Nominal conditions, Verdict `MONITOR`, valid data provenance, absence of any "Demo" watermark.

### Scene 2: Meteorological Escalation & Selective Recalculation (0:45 - 1:45)
* Trigger next step:
  ```bash
  python scripts/run_showcase.py next
  ```
* Observe:
  * Backend logs: Selective recalculation reusing Exposure & Vulnerability, recomputing Hazard & Risk.
  * Mobile Notification pop-up: `Decision Update [PROCEED_WITH_CAUTION]`.
  * Mobile UI update: NirnayCard seamlessly updates to Revision 2.

### Scene 3: Official Alert & Decision Revision (1:45 - 2:30)
* Trigger warning step:
  ```bash
  python scripts/run_showcase.py next
  ```
* Observe:
  * Red Alert notification received.
  * NirnayCard updates to Verdict `POSTPONE`, Severity `HIGH`.
  * Show Decision Revision history showing Revision 1 -> Revision 2 -> Revision 3 lineage.

### Scene 4: Offline Resilience & Reconnection (2:30 - 3:30)
* Turn on Airplane Mode on device.
* Show: Status transitions to `OFFLINE VERIFIED`, last verified assessment stays visible.
* Turn off Airplane Mode.
* Show: Status indicator transitions to `RECOVERING`, incremental synchronization executes, latest verified assessment confirmed.

---

## 6. Truthful Demonstration Claims

| Allowed Video Claims | Strictly Prohibited Claims |
| :--- | :--- |
| "Evidence-first deterministic decision pipeline" | "This is a live government transmission from IMD" |
| "Selective stage recalculation on weather changes" | "Live CWC river sensors are broadcasting in real-time" |
| "Cryptographically hashed audit lineage" | "Zero data loss guaranteed in catastrophic flooding" |
| "On-device resilience and offline cache preservation" | "Autonomous statutory evacuation decreed by AI" |
| "LLM-independent analytical calculation" | "Unverified simulation" |

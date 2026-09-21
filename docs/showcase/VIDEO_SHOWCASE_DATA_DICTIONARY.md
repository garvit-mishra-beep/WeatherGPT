# VAYUBODHAK VIDEO SHOWCASE — DATA DICTIONARY

## 1. Overview & Data-Truth Integrity

The VAYUBODHAK Video Showcase operates on **Controlled Scenario Inputs** passing through the **Real End-to-End Analytical Pipeline**. In accordance with scientific integrity and operational transparency rules:
* Showcase records are strictly designated as **Controlled Demonstrative Data** (`DATA_CLASS: CONTROLLED_SCENARIO`).
* They are **NEVER** falsely represented as live, real-time transmissions from statutory bodies (IMD, CWC, NDMA, GSI).
* Provenance, payload hashes, temporal windows, and quality states are rigorously maintained matching canonical Phase 2A/9A/9C schemas.

---

## 2. Location & Geographic Bounds

* **Canonical Showcase Region**: Gwalior District, Madhya Pradesh, India
* **Bounding Box**: `[25.80°N, 78.00°E]` to `[26.40°N, 78.40°E]`
* **Centroid**: `26.2183°N, 78.1828°E`
* **Administrative Code**: `IN-MP-GWL`
* **State**: Madhya Pradesh

---

## 3. Dataset Fixtures Inventory (`data/showcase/`)

### 3.1 `scenario_manifest.json`
Defines the multi-step deterministic showcase trajectory.
* **Fields**:
  * `scenario_name`: `"monsoon_escalation_gwalior"`
  * `location`: District coordinates and bounds
  * `steps`: Sequence of scenario events from Step 0 to Step 5
  * `expected_transitions`: Stage execution and revision triggers
  * `offline_step`: Simulation of network disconnection
  * `recovery_step`: Incremental synchronization reconciliation

### 3.2 `weather_initial.json` (Step 0 Baseline Input)
Represents nominal, calm monsoon conditions.
* `record_id`: `"SHOWCASE-REC-001"`
* `source_id`: `"OPEN_METEO"`
* `source_class`: `"OBSERVATION"`
* `rainfall_mm`: `3.0` (Nominal, below 5.0mm threshold)
* `temperature_c`: `28.5`
* `wind_speed_kmh`: `12.5`
* `relative_humidity_pct`: `68.0`
* `quality_state`: `"VALID"`
* `freshness_state`: `"FRESH"`
* **Expected Real Analytical Outcome**: Hazard: LOW (0.12), Risk: LOW, Decision: `MONITOR` (Revision 1)

### 3.3 `weather_rain_increase.json` (Step 1 Escalation Input)
Represents sudden convective downpour crossing critical operational thresholds.
* `record_id`: `"SHOWCASE-REC-002"`
* `source_id`: `"OPEN_METEO"`
* `source_class`: `"OBSERVATION"`
* `rainfall_mm`: `88.5` (Crosses 2.5mm delta and 64.5mm heavy rain threshold)
* `temperature_c`: `24.0`
* `wind_speed_kmh`: `42.0`
* `relative_humidity_pct`: `94.0`
* `quality_state`: `"VALID"`
* `freshness_state`: `"FRESH"`
* **Expected Real Analytical Outcome**: Hazard: MODERATE (0.58), Risk: MODERATE, Decision: `PROCEED_WITH_CAUTION` (Revision 2), Selective Recalculation: Exposure & Vulnerability reused, Hazard & Risk recomputed.

### 3.4 `warning_update.json` (Step 2 Statutory Red Alert Input)
Represents an authoritative meteorological warning bulletin.
* `record_id`: `"SHOWCASE-REC-003"`
* `source_id`: `"IMD"` (Statutory Authority E1)
* `source_class`: `"OFFICIAL_WARNING"`
* `warning_level`: `"RED"`
* `hazard_type`: `"FLASH_FLOOD_AND_HEAVY_DOWNPOUR"`
* `confidence`: `0.92`
* `quality_state`: `"VALID"`
* `freshness_state`: `"FRESH"`
* **Expected Real Analytical Outcome**: Hazard: HIGH (0.85), Risk: HIGH, Decision: `POSTPONE` (Revision 3), Notification: Alert dispatched, Sync cursor advanced.

### 3.5 `exposure_snapshot.json` (Controlled Geographic Exposure)
Real-world aligned baseline assets within Gwalior District bounds.
* **Road Segments**:
  * `ROAD-GWL-01`: National Highway NH-44 (Criticality: 0.90, Flood Elevation: 210m)
  * `ROAD-GWL-02`: State Highway SH-19 (Criticality: 0.70, Flood Elevation: 205m)
* **Critical Facilities**:
  * `FAC-GWL-HOSP-01`: Gwalior District Hospital (Criticality: 0.95, Low-lying flood risk)
  * `FAC-GWL-SCH-01`: Government Higher Secondary School Morar (Shelter: Designated)
* **Agricultural Land**:
  * `AGRI-GWL-ZONE-A`: 184,500 Hectares (Paddy / Pearl Millet crop stage: active flowering)

### 3.6 `vulnerability_snapshot.json` (Physical & Structural Vulnerability)
* **Drainage Coefficient**: `0.38` (Constrained urban & semi-urban runoff capacity)
* **Structural Exposure Index**: `0.65`
* **Socio-Economic Fragility**: `0.48`

---

## 4. Provenance & Operational Event Schema

Every ingested showcase operational record adheres to the Phase 9C Event Contract:
```json
{
  "event_id": "EVT-SHOWCASE-001",
  "event_type": "WEATHER_UPDATE",
  "source_id": "OPEN_METEO",
  "source_authority": "E2",
  "source_record_id": "SHOWCASE-REC-001",
  "sequence_number": 1,
  "correlation_id": "CORR-SHOWCASE-GWL-001",
  "payload_hash": "sha256-hash-of-payload",
  "ingested_at": "2026-09-21T09:00:00Z",
  "valid_from": "2026-09-21T09:00:00Z",
  "valid_to": "2026-09-21T15:00:00Z",
  "quality_state": "VALID",
  "freshness_state": "FRESH",
  "processing_status": "APPLIED"
}
```

---

## 5. User-Facing Display Guidelines

| System State | Permitted UX Display | Prohibited Developer Terminology |
| :--- | :--- | :--- |
| Baseline Showcase | `Controlled Scenario • Operational` | `Demo Mode`, `Mock Data`, `Test Mode` |
| Degraded / Offline | `Offline • Last Verified State` | `Offline Demo Mode`, `Mock Network` |
| Local In-Memory Mode | `Local Intelligence Engine` | `Demo Engine`, `Fake Pipeline` |
| Cache Retrieval | `Verified Offline Cache` | `Demo Cache`, `Mock Storage` |

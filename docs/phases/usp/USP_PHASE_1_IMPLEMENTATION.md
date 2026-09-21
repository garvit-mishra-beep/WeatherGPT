# Vayubodhak USP Phase 1 — Evidence to Decision

## 1. Objective

Phase 1 establishes the foundational Unique Selling Proposition (USP) of Vayubodhak: **Evidence → Decision → NirnayCard**.

Traditional meteorological assistants stop at regurgitating raw numerical forecasts or narrative summaries (e.g., *"Tomorrow will be 32 °C with 60% chance of rain"*). Farmers, field operators, and agricultural managers do not just need raw data; they need **direct, unambiguous operational decisions** (such as *"Should I spray my cotton tonight?"*) grounded in verified physical evidence, rigorous agronomic thresholds, and complete auditability.

Phase 1 implements:
1. **The Canonical `EvidenceBundle`**: A standardized schema aggregating physical weather variables, multi-provider surface observations, numerical weather prediction (NWP) guidance, official disaster alerts, data quality checks, units, and explicit metadata provenance.
2. **Deterministic `DecisionEngine`**: A zero-LLM decision engine that evaluates operational questions against physical constraints, produces categorical verdicts (`GO`, `POSTPONE`, `NO_GO`, `PROCEED_WITH_CAUTION`), and assigns risk severities without hallucination or numerical drift.
3. **The Canonical `NirnayCard`**: The standardized user-facing decision contract containing the direct verdict, recommended action, explicit physical justification ("why"), quantified impact, operational alternatives, evidence summary, and audit ledger.
4. **`EvidenceLedger` Audit Foundation**: A deterministic traceability trail mapping every decision through its inputs, threshold rules, calculation formulas, sources, and execution timestamps.
5. **WRF Honesty & LLM Independence**: Strict architectural guarantees that the system never fabricates unconfigured models (such as WRF) or relies on an online LLM cluster to produce a sound operational decision.

---

## 2. Core USP

The core architecture of Vayubodhak transforms raw meteorological signals into decisive, verifiable action:

$$\text{Data} \longrightarrow \text{Evidence} \longrightarrow \text{Intelligence} \longrightarrow \text{Uncertainty} \longrightarrow \text{Decision} \longrightarrow \text{Action} \longrightarrow \text{Proof}$$

* **Data**: Raw surface weather observations, satellite feeds, NWP grids (NOAA GFS 0.25°), and CAP alerts.
* **Evidence**: Sanitized, quality-controlled, unit-verified values bundled with provider provenance and valid time envelopes (`EvidenceBundle`).
* **Intelligence**: Domain-specific physical formulas (FAO-56 Penman-Monteith $ET_0$, chemical spray drift criteria, water balance models).
* **Uncertainty**: Transparent assessment of forecast lead times, observation freshness, single-model dependency, and unavailable regional models.
* **Decision**: Deterministic rule evaluation yielding an unambiguous operational verdict (`NirnayCard`).
* **Action**: Concrete operational commands and timing guidance for the end user.
* **Proof**: Cryptographically and logically inspectable audit record (`EvidenceLedger`) linking the outcome to exact inputs and physical thresholds.

---

## 3. Existing Architecture

During Step 1 inspection, the following existing production services and deterministic components were discovered and integrated:

1. **`WeatherProviderManager` (`app/adapters/weather_manager.py`)**:
   - Manages resilient, circuit-broken external adapters for surface weather (Open-Meteo, OpenWeather, WeatherAPI, Tomorrow.io).
   - Ingests official IMD / NDMA Sachet Common Alerting Protocol (CAP) XML warnings with immutable severity (`Green`, `Yellow`, `Orange`, `Red`).
2. **`GFSProvider` (`app/adapters/gfs/client.py`)**:
   - Ingests NOAA GFS 0.25° NWP atmospheric grids covering the Indian bounding box ($6^\circ\text{N} - 38^\circ\text{N}$, $68^\circ\text{E} - 98^\circ\text{E}$).
3. **`WRFProvider` (`app/adapters/wrf/client.py`)**:
   - Provides a client boundary for High-Resolution Weather Research and Forecasting (WRF) data.
   - When unconfigured, it reports `ProviderQuality.UNAVAILABLE` and `WRFStatus.UNAVAILABLE`.
4. **Deterministic Analytics Engine (`app/analytics/`)**:
   - `app/analytics/water_balance.py`: Contains `evaluate_spray_window()` with strict physical thresholds:
     - Wind speed $\le 15.0\text{ km/h}$ (drift hazard prevention).
     - Rain probability $\le 30.0\%$ (wash-off risk prevention).
     - Consecutive rain-free window of $\ge 4\text{ hours}$ post-application ($0.0\text{ mm}$ rain).
   - `app/analytics/fao56.py`: Penman-Monteith reference evapotranspiration ($ET_0$).
   - `app/analytics/risk.py`: Composite operational risk scoring ($I = 0.50 \times H + 0.30 \times E + 0.20 \times V$).
5. **Administrative Boundaries & GIS (`app/gis/`)**:
   - PostGIS reverse-geocoding hierarchy (Country $\to$ State $\to$ District $\to$ SubDistrict) and bounding box verification.

---

## 4. EvidenceBundle

The `EvidenceBundle` (`app/decision/models.py`) encapsulates all verified meteorological evidence required for operational decision-making.

### Schema Fields
* `bundle_id` (`str`): Unique deterministic identifier with prefix `eb_` and UUID.
* `location` (`LocationContext`): Normalized spatial coordinates (`latitude`, `longitude`, `name`, `district`, `state`).
* `requested_time` (`str`): ISO 8601 timestamp representing the target operational horizon.
* `valid_time` (`Dict[str, str]`): Temporal validity envelope containing `start` and `end` ISO timestamps.
* `observations` (`Dict[str, Any]`): Real-time surface parameters:
  - `temperature_c` (Float, °C)
  - `relative_humidity_pct` (Float, %)
  - `wind_speed_kmh` (Float, km/h)
  - `wind_gust_kmh` (Float, km/h)
  - `precipitation_mm` (Float, mm)
  - `units` (Standard metric mapping: `temperature: °C`, `wind_speed: km/h`, etc.)
* `forecast` (`Dict[str, Any]`): Short-range prognostic horizon parameters:
  - `rain_probability_pct` (Float, %)
  - `rainfall_total_mm` (Float, mm)
  - `wind_speed_kmh` (Float, km/h)
  - `post_spray_rain_mm_4h` (Float, mm)
* `alerts` (`List[Dict[str, Any]]`): Immutable official CAP warning payloads (IMD/NDMA).
* `model_information` (`Dict[str, Any]`): Atmospheric model status:
  - `gfs`: Operational status, resolution (`0.25 deg`), run cycle.
  - `wrf`: Operational status (`unavailable` when unconfigured), reason.
* `source_information` (`List[Dict[str, Any]]`): Data provider provenance (e.g., `Open-Meteo`, `IMD Sachet`, `NOAA GFS`), datasets, fetch timestamps, and `is_official` flags.
* `quality` (`Dict[str, Any]`): Quality control results:
  - `freshness`: `fresh` (< 60 min), `stale`, or `unknown`.
  - `qc_passed`: Boolean flag indicating physical range sanity.
  - `qc_checks`: List of sanity validations (e.g. $-50 \le T \le 60$, $0 \le RH \le 100$, $0 \le W \le 200$).
* `calculations` (`Dict[str, Any]`): Deterministic mathematical outputs (spray suitability, vapor pressure, $ET_0$).
* `uncertainty` (`Dict[str, Any]`): Data availability, single-model dependency, and WRF absence.
* `limitations` (`List[str]`): Explicit, unvarnished operational caveats.

---

## 5. Decision Engine

The `DeterministicDecisionEngine` (`app/decision/engine.py`) takes an `EvidenceBundle` and operational question, returning a `NirnayCard`.

### Deterministic Rules
The decision engine evaluates constraints strictly in software:
1. **Severe Weather Alert Override**:
   - Official IMD Red/Orange warnings immediately force `verdict = NO_GO` with `severity = CRITICAL` or `HIGH`.
2. **Farmer Chemical Spray Rules (`app/analytics/water_balance.py`)**:
   - **Wind Drift Rule**: Observed or forecast wind speed must be $\le 15.0\text{ km/h}$. If $> 15.0\text{ km/h}$, droplets drift off-target, contaminating non-target zones or evaporating before deposition.
   - **Precipitation Probability Rule**: Precipitation probability must be $\le 30.0\%$. High rain chance washes active ingredients into the soil before absorption.
   - **Rain-Free Window Rule**: Total rainfall in the 4 hours post-application must be $0.0\text{ mm}$.
3. **General Operational Work Rules**:
   - Lightning, squalls, or heavy rain ($> 30\text{ mm}$) trigger `NO_GO` or `POSTPONE`.

### Uncertainty Handling
- If only GFS data is available and WRF is unconfigured, the engine marks `confidence = MEDIUM` (or `HIGH` only when surface obs and radar confirm short-term trends).
- Statements never invent multi-model consensus.

---

## 6. NirnayCard

The `NirnayCard` (`app/decision/models.py`) is the canonical response contract:

```json
{
  "question": "Should I spray my cotton tonight?",
  "verdict": "POSTPONE",
  "severity": "MODERATE",
  "recommended_action": "Do NOT spray cotton tonight. Postpone application to prevent chemical wash-off and droplet drift.",
  "action_window": {
    "status": "unavailable",
    "recommended_start": null,
    "recommended_end": null,
    "note": "Next optimal spray window will be computed once wind speeds drop below 15 km/h."
  },
  "confidence": "HIGH",
  "uncertainty": {
    "wrf_regional_available": false,
    "models_evaluated": ["GFS_0.25"],
    "statement": "Decision grounded in GFS 0.25° NWP and verified surface observations. WRF regional model is unconfigured."
  },
  "why": [
    "Surface wind speed is 18.5 km/h, exceeding the maximum safe agronomic spraying limit of 15.0 km/h (severe risk of chemical drift).",
    "Rain probability is 20.0%, which is within acceptable limits (<= 30%)."
  ],
  "impact": {
    "chemical_wastage": "High (droplet drift reduces pesticide deposition on cotton leaves by 35-50%).",
    "financial_loss": "Estimated loss of chemical investment plus cost of repeated application.",
    "environmental_risk": "Off-target chemical contamination to adjacent crops or water bodies."
  },
  "alternatives": [
    "Re-evaluate conditions tomorrow morning (06:00 - 09:00 AM) when thermal inversion typically dampens surface winds.",
    "If pest infestation is critical, consider low-drift air-induction spray nozzles."
  ],
  "evidence": {
    "temperature_c": 28.0,
    "wind_speed_kmh": 18.5,
    "wind_threshold_kmh": 15.0,
    "rain_probability_pct": 20.0,
    "rain_threshold_pct": 30.0,
    "alerts_active": 0,
    "sources": ["Open-Meteo", "NOAA GFS 0.25°"]
  },
  "ledger": { ... }
}
```

---

## 7. Evidence Ledger

The `EvidenceLedger` provides an auditable trail:

$$\text{Decision} \longrightarrow \text{Inputs} \longrightarrow \text{Rules} \longrightarrow \text{Calculations} \longrightarrow \text{Sources} \longrightarrow \text{Timestamps} \longrightarrow \text{Output}$$

Each evaluated rule is captured in `LedgerRuleEvaluation`:
* `rule_name`: Machine identifier (e.g. `wind_drift_safety_threshold`).
* `rule_description`: Human-readable agronomic rule definition.
* `observed_value`: Physical value extracted from evidence ($18.5$).
* `threshold`: Agronomic threshold ($15.0$).
* `operator`: Comparison operator (`<=`).
* `unit`: Physical unit (`km/h`).
* `satisfied`: Boolean pass/fail outcome (`false`).
* `severity_if_failed`: Resulting operational risk tier (`MODERATE`).

---

## 8. Farmer Spray Decision

### Query: *"Should I spray my cotton tonight?"*
The end-to-end execution flow:
```
User Query: "Should I spray my cotton tonight?"
     │
     ▼
API Endpoint (POST /api/v1/decisions)
     │
     ▼
EvidenceBundleBuilder (app/decision/evidence_builder.py)
  ├── Queries Open-Meteo for Gwalior surface obs (T=28.0°C, RH=60%, Wind=18.5 km/h)
  ├── Queries GFS 0.25° prognostic forecast (Rain Prob=20%, Precip=0.0 mm)
  ├── Checks IMD / Sachet CAP alerts (No active warnings)
  ├── Audits WRF availability -> Marks unconfigured
  └── Executes physical QC checks -> PASSED
     │
     ▼
DeterministicDecisionEngine (app/decision/engine.py)
  ├── Reuses evaluate_spray_window() from app/analytics/water_balance.py
  ├── Evaluates Wind (18.5 km/h <= 15.0 km/h) -> FAILS (drift hazard)
  ├── Evaluates Rain Prob (20% <= 30%) -> PASSES
  ├── Evaluates Rain Volume (0.0 mm == 0.0 mm) -> PASSES
  ├── Synthesizes Cotton-specific impact (foliar deposition loss, pest risk)
  └── Compiles EvidenceLedger rule trace
     │
     ▼
NirnayCard Output: Verdict = POSTPONE (Delivered in < 25 ms, 0 LLM tokens)
```

---

## 9. WRF Honesty Rule

**Mandatory meteorological truth constraint:**
- WRF (Weather Research and Forecasting) must **NEVER** be claimed as available unless a legitimate local or regional WRF model stream is actively configured in `app.config.Settings`.
- The system must **NEVER** report:
  - *"GFS and WRF agree"*
  - *"Multi-model consensus confirms"*
  when WRF is unavailable.
- In Phase 1, `EvidenceBundleBuilder` queries `wrf_provider.status`. If unconfigured:
  - `model_information["wrf"]["status"] = "unavailable"`
  - `model_information["wrf"]["reason"] = "No legitimate live stream configured; WRF regional model is unconfigured."`
  - Appends to `limitations`: `"WRF regional model is not configured; forecast relies on GFS 0.25° / Open-Meteo guidance. No multi-model divergence computed."`
  - `NirnayCard.uncertainty["wrf_regional_available"] = False`.

---

## 10. LLM Independence

**Phase 1 does NOT require Ollama or Gemma:**
- The entire decision intelligence pipeline (data gathering, QC, threshold comparison, verdict determination, impact assessment, and ledger building) is executed in pure, verified Python.
- If `OLLAMA_ENABLED=false` or if the remote LLM cluster (`UJJWAL`) is completely powered down, disconnected, or unreachable, `POST /api/v1/decisions` returns a 100% complete, valid `NirnayCard`.
- Future phases will use the LLM strictly as an optional peripheral translation/conversational synthesizer.

---

## 11. API

### Route
`POST /api/v1/decisions`

### Request Schema (`DecisionRequest`)
```json
{
  "question": "Should I spray my cotton tonight?",
  "location": {
    "name": "Gwalior",
    "latitude": 26.2183,
    "longitude": 78.1828,
    "district": "Gwalior",
    "state": "Madhya Pradesh"
  },
  "requested_time": "2026-09-07T19:00:00+05:30",
  "domain": "farmer",
  "context": {
    "crop_name": "Cotton",
    "chemical": "Insecticide"
  },
  "custom_bundle": null
}
```

### Response Schema (`NirnayCard`)
Returns the canonical `NirnayCard` JSON payload documented in Section 6.

---

## 12. Testing

The Phase 1 decision layer is thoroughly tested with 8 deterministic tests in `tests/test_usp_phase1_decisions.py`:

| Test Name | Type | Coverage | Result |
| :--- | :--- | :--- | :--- |
| `test_evidence_bundle_schema_completeness` | Unit | Verifies all required fields, units, QC metadata, timestamps | **PASSED** |
| `test_wrf_honesty_rule_in_evidence_bundle` | Unit | Verifies WRF marked unavailable, reason recorded, no fake consensus | **PASSED** |
| `test_golden_spray_decision_high_wind_postpone` | Golden / Unit | Wind $18.5\text{ km/h} > 15.0\text{ km/h} \to \text{POSTPONE}$, drift warning, ledger audit | **PASSED** |
| `test_golden_spray_decision_rain_hazard_postpone` | Golden / Unit | Rain prob $65\% > 30\% \to \text{POSTPONE}$, wash-off risk, ledger audit | **PASSED** |
| `test_golden_spray_decision_optimal_conditions_go` | Golden / Unit | Wind $8.5\text{ km/h}$, Rain $10\% \to \text{GO}$, optimal window confirmed | **PASSED** |
| `test_official_red_alert_forces_no_go` | Unit | Official IMD Red Warning overrides weather $\to \text{NO\_GO}$ (Critical) | **PASSED** |
| `test_api_decisions_spray_cotton_endpoint` | Integration | Full HTTP API call with live weather provider ingestion | **PASSED** |
| `test_api_decisions_with_deterministic_fixture` | Integration | Full HTTP API call with offline fixture bundle ($0\text{ network ops}$) | **PASSED** |

**Summary: 8 passed in 52.00s.**

---

## 13. Files Changed / Created

| File | Action | Purpose |
| :--- | :--- | :--- |
| `app/decision/__init__.py` | Created | Package export for decision models, builder, and engine. |
| `app/decision/models.py` | Created | Pydantic schemas: `EvidenceBundle`, `NirnayCard`, `EvidenceLedger`, `LedgerRuleEvaluation`, `DecisionRequest`. |
| `app/decision/evidence_builder.py` | Created | Builds `EvidenceBundle` from live providers with QC, units, and WRF honesty check. |
| `app/decision/engine.py` | Created | Deterministic decision engine evaluating spray, irrigation, and weather rules. |
| `app/api/v1/decisions.py` | Created | REST API route `POST /api/v1/decisions`. |
| `app/api/v1/router.py` | Modified | Registered `decisions_router` under `/api/v1`. |
| `app/dependencies/container.py` | Modified | Registered `evidence_bundle_builder` and `decision_engine` singletons in `AppContainer`. |
| `app/dependencies/providers.py` | Modified | Added FastAPI `Depends` helpers `get_decision_engine` and `get_evidence_bundle_builder`. |
| `tests/test_usp_phase1_decisions.py` | Created | 8 automated tests (schema, WRF honesty, golden decisions, API contracts). |
| `docs/USP_PHASE_1_IMPLEMENTATION.md` | Created | Comprehensive engineering documentation (this document). |

---

## 14. Remaining USP Roadmap

The following phases represent the planned technical sequence. None of these are implemented in Phase 1:

* **Phase 2 — Action Window Engine**: Algorithmic forward-scanning of hourly NWP forecast matrices to compute specific forward-looking execution windows (e.g. *"Best window: Tomorrow 06:00 - 09:30 AM"*).
* **Phase 3 — Uncertainty Engine Enhancement**: Advanced ensemble spread quantification, spatial confidence calibration, and multi-NWP divergence metrics when multiple models are configured.
* **Phase 4 — Evidence Ledger Storage & Merkle Proofs**: Persistent database ledger backing with cryptographic hash chains to prove decision integrity for agricultural insurance and legal audits.
* **Phase 5 — Impact Intelligence**: Domain-specific economic loss calculators (rupee cost per hectare, crop-specific foliar damage, and supply chain disruption modeling).
* **Phase 6 — What-If Simulation**: Interactive hypothetical parameter perturbation (e.g. *"What if rain begins 2 hours earlier?"* or *"What if wind gusts reach 25 km/h?"*).
* **Phase 7 — Alert → Impact → Action**: Real-time push notification pipelines mapping IMD CAP alerts directly to precomputed agricultural actions for registered farmer plots.
* **Phase 8 — Multilingual Decision Intelligence**: Multilingual synthesis ensuring numerical invariance across Hindi, Marathi, Gujarati, and Bengali.

---

## 15. Known Limitations

1. **Action Window Computation is Static in Phase 1**: Implemented and upgraded in Phase 2 via `ActionWindowEngine`.
2. **WRF Integration is Unconfigured**: Live WRF regional feeds are not connected; single-model GFS 0.25° is used and reported honestly.
3. **Ledger Persistence**: The `EvidenceLedger` is generated in memory and returned inside `NirnayCard`; database persistence and cryptographic hashing are scheduled for Phase 4.
4. **Android UI**: Android UI for NirnayCard is not yet built; the existing mobile client continues to interact with the standard chat endpoints, with full Nirnay cards ready for consumption via `POST /api/v1/decisions`.

---

# Phase 2 — Action Window Engine

## 1. Objective

Phase 2 upgrades the Vayubodhak decision system from simply issuing negative prohibitions (*"Do not spray tonight"*) to delivering positive, proactive operational scheduling:

> **"Don't just tell me what NOT to do. Tell me WHEN I SHOULD DO IT."**

When an operational task (such as chemical spraying) is postponed due to adverse real-time conditions (e.g., wind drift, rain wash-off), the **Action Window Engine** deterministically evaluates forward hourly forecast matrices to discover, score, and rank valid future execution windows.

## 2. Architecture & Pipeline

```text
EvidenceBundle (Hourly Forecast Time-Series)
     │
     ▼
ActionWindowEngine (app/decision/action_window.py)
  ├── 1. Hourly Point Extraction (Wind, Rain Prob, Precipitation)
  ├── 2. Canonical Agronomic Constraint Evaluation (evaluate_spray_window)
  ├── 3. Contiguous Passing Hour Streak Accumulation
  ├── 4. Window Boundary Segmentation (Splits on invalid hours)
  ├── 5. Minimum Duration Verification (Configurable: >= 2 hours)
  ├── 6. Deterministic Multi-Criteria Window Scoring (0.0 to 100.0)
  └── 7. Best Window & Fallback Ranking
     │
     ▼
NirnayCard (action_window = ActionWindow)
  ├── status: available / unavailable
  ├── best_window: ActionWindowPeriod (Recommended)
  ├── fallback_windows: List[ActionWindowPeriod]
  ├── why: Enhanced with window timing & physical metrics
  ├── alternatives: Populated with actionable execution hours
  └── EvidenceLedger: Complete candidate-hour evaluation trace
```

## 3. Hourly Forecast Evaluation & Constraints

The engine reuses canonical thresholds defined in `app/analytics/water_balance.py`:
* **Maximum Wind Speed**: $15.0\text{ km/h}$ (`SPRAY_MAX_WIND_SPEED_KMH`). Excess winds cause foliar droplet drift and environmental contamination.
* **Maximum Rain Probability**: $30.0\%$ (`SPRAY_MAX_RAIN_PROBABILITY_PCT`). Elevated convective rain risk prevents pesticide absorption.
* **Maximum Post-Spray Rain**: $0.0\text{ mm}$ (`SPRAY_MAX_POST_RAIN_MM`). Active ingredients are dissolved and lost if precipitation occurs post-application.

Every forecast hour $h_i$ is evaluated into a `CandidateHourEvaluation`:
$$\text{passed}(h_i) = (\text{wind}_i \le 15.0) \land (\text{rain\_prob}_i \le 30.0) \land (\text{precip}_i \le 0.0)$$

## 4. Window Generation & Operational Sufficiency

* **Contiguous Grouping**: Consecutive passing hours are grouped into a candidate window period. Any failing hour immediately splits the window.
* **Operational Sufficiency vs. Meteorological Validity**: An isolated passing hour (e.g., 1 calm hour surrounded by gale-force winds) is meteorologically valid but operationally insufficient for farm operations (mixing, nozzle calibration, field transit, and application). The engine enforces a configurable `min_spray_window_hours = 2`.
* **Interval Representation**: Start time is the ISO timestamp of the first valid hour; end time is the completion timestamp of the last valid hour (e.g. 06:00 to 10:00 represents a 4-hour window: 06:00, 07:00, 08:00, 09:00).

## 5. Deterministic Multi-Criteria Window Scoring

Qualified windows are ranked by a deterministic, bounded scoring function $S \in [0.0, 100.0]$:
$$S = S_{\text{wind}} + S_{\text{rain}} + S_{\text{duration}} + S_{\text{proximity}}$$

1. **Wind Calmness ($S_{\text{wind}} \in [0, 40]$)**:
   $$S_{\text{wind}} = 40.0 \times \max\left(0.0, \frac{15.0 - \overline{\text{wind}}}{15.0}\right)$$
2. **Rain Probability Safety ($S_{\text{rain}} \in [0, 30]$)**:
   $$S_{\text{rain}} = 30.0 \times \max\left(0.0, \frac{30.0 - \text{max\_rain\_prob}}{30.0}\right)$$
3. **Operational Duration ($S_{\text{duration}} \in [0, 20]$)**:
   $$S_{\text{duration}} = \min(20.0, \text{duration\_hours} \times 5.0)$$
4. **Proximity Prioritization ($S_{\text{proximity}} \in [0, 10]$)**:
   $$S_{\text{proximity}} = \max(0.0, 10.0 - 0.2 \times \text{lead\_hours})$$

Ties are resolved deterministically by earlier start timestamp.

## 6. Best + Fallback Selection

* The highest-scoring window is designated as `best_window` (`recommended=True`).
* The remaining valid windows (up to 3) are populated as `fallback_windows`.
* If no candidate window satisfies the constraints:
  `status = "unavailable"`, `best_window = None`, and `reason` provides an unvarnished physical explanation.

## 7. Uncertainty & WRF Honesty Rule

* In Phase 2, the Action Window Engine adheres strictly to the WRF Honesty Rule:
  - If WRF is unconfigured, the window explanation states: `"Guidance derived from GFS 0.25° NWP; independent regional WRF comparison is unconfigured."`
  - The system **never claims model consensus or agreement**.
  - `uncertainty.wrf_regional_available` remains `False`.

## 8. Evidence Traceability & Ledger Trace

Every candidate hour evaluated by the Action Window Engine is recorded in the `EvidenceLedger`:
1. `rules`: Includes `forward_action_window_search` rule evaluation with observed window summary and pass/fail state.
2. `calculations.action_window_scan`: Includes total hours evaluated, valid hours count, best window metrics, score breakdown, and fallback window count.

## 9. Testing & Validation

Tested via comprehensive automated test suite `tests/test_usp_phase2_action_window.py` (10 passed in 26.68s):
* **Fixture A**: Consecutive valid hours $\to$ Single qualified window.
* **Fixture B**: High wind splits windows $\to$ 2 separate windows produced.
* **Fixture C**: Rain probability spike splits windows $\to$ 2 separate windows produced.
* **Fixture D**: Active rainfall $\to$ Window rejected.
* **Fixture E**: Persistent high winds $\to$ `status: unavailable` reported honestly.
* **Fixture F**: Multiple valid windows $\to$ Calmer window ranked top, secondary in fallback.
* **Fixture G**: Incomplete forecast $\to$ `status: unavailable`, `confidence: LOW`.
* **Operational Sufficiency**: 1-hour isolated spike rejected when `min_hours=2`.
* **Golden Cotton Spray Test**: Tonight postponed due to wind ($18.5\text{ km/h}$) $\to$ Action Window Engine identifies tomorrow morning (06:00 - 10:00) with complete ledger trace.
* **REST API Contract Test**: `POST /api/v1/decisions` returns populated `action_window`.

## 10. Phase 2 Limitations

1. **Static Crop Rules**: Phase 2 optimizes chemical spraying for cotton/field crops. Crop-specific canopy penetration rules for tree orchards or submerged paddy are deferred to future domain brains.
2. **WRF Unconfigured**: Relies on GFS 0.25° NWP; multi-model divergence analysis is deferred to Phase 3.
3. **No Dynamic Rerouting in UI**: Full mobile UI for interactive action-window selection is scheduled for post-backend phases.


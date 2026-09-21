# Phase 8 — Personalized Weather Intelligence & Proactive Decision Engine

**System:** Vayubodhak (WeatherGPT)  
**Document:** `docs/PHASE_8_PROACTIVE_WEATHER_INTELLIGENCE.md`  
**Phase:** 8  
**Authority:** [`AGENTS.md`](../AGENTS.md)  
**Status:** COMPLETE & VERIFIED (100% Deterministic Operation, 0 LLM Dependency)

---

## 1. Executive Summary

Phase 8 elevates Vayubodhak from a reactive question-and-answer assistant into an autonomous, proactive weather-decision intelligence engine. Rather than expecting farmers or outdoor workers to continuously poll the system ("Should I spray today?", "Can I irrigate tomorrow?"), the Phase 8 engine continuously monitors changing meteorological evidence, detects actionable state transitions (e.g., $GO \to POSTPONE$, window disappearance, approaching CAP alerts), and generates deterministic, evidence-grounded **WeatherDecisionEvents**.

The engine strictly complies with all core architectural invariants:
- Zero data fabrication (mandatory caveats for unmeasured soil moisture and default crop stages).
- Official severe weather warning immutability (NDMA Sachet CAP alerts override all forecast operations).
- Mathematical calculations remain strictly deterministic (FAO-56 Penman-Monteith $ET_0$, water balance, spray drift/washoff limits, Douglas-Peucker spatial matching).
- Gemma/LLM is strictly optional and explanation-only; the entire proactive decision lifecycle operates offline without Ollama.
- Event generation is cleanly decoupled from transport notification delivery; transport dropouts never mutate or destroy verified decision events.
- Anti-spam deduplication engine guarantees zero notification storming via SHA-256 stable key hashing, 6-hour cooldown intervals, and severity escalation bypasses.

---

## 2. Problem Addressed

Traditional weather notification systems suffer from two chronic flaws:
1. **Generic Raw Forecast Spam:** Pushing generic alerts like *"20% chance of rain at 3 PM"* or *"Temperature is 34°C"*, forcing users to manually calculate what that means for their crops, work, or safety.
2. **Notification Storming & Repetition:** Repeatedly firing alerts for unchanged conditions, training users to mute or ignore weather notifications.

Phase 8 solves this by asking:
> *"What meaningful, weather-driven operational decision does this specific user or farmer need to know now or soon?"*

Events are only emitted when a deterministic verdict changes or an authoritative hazard threshold is breached.

---

## 3. Existing Architecture Reused

In strict adherence to the mandate (*"Do NOT redesign Phases 1–7. Do NOT create duplicate logic."*), Phase 8 reuses and coordinates existing production services:

| Component | Repository Location | Reused Role in Phase 8 |
| :--- | :--- | :--- |
| **Evidence Bundle Builder** | `app/decision/evidence_builder.py` | Assembles physical observations, multi-model NWP, CAP alerts, and source provenance. |
| **Deterministic Decision Engine** | `app/decision/engine.py` | Evaluates multi-rule operational Ledgers ($GO$, $POSTPONE$, $NO\_GO$). |
| **Alert Impact Engine** | `app/decision/alert_impact.py` | Spatial point-in-polygon containment (`ST_Covers`), $H \times E \times V$ operational risk scoring, official alert immutability. |
| **Action Window Engine** | `app/decision/action_window.py` | Continuous hourly forward scanning for operational feasibility (e.g. spray windows). |
| **Farmer Registry & Analytics** | `app/farmer/analytics.py` | FAO-56 Penman-Monteith $ET_0$, soil water balance, harvest window scanning, sowing/fieldwork evaluation. |
| **Farmer Plot Repository** | `app/db/repositories/farmer.py` | Queries registered farmer plots and crop geometries in PostgreSQL 18 + PostGIS 3.6. |
| **Explanation Bridge** | `app/decision/explanation_bridge.py` | Decoupled local language narrative generation with deterministic fallback. |

---

## 4. Phase 8 Architecture

```text
               Official NDMA Sachet CAP Alerts / Operational Observations / NWP
                                              │
                                              ▼
                                 [EvidenceBundleBuilder]
                                              │
                                              ▼
                             [ProactiveDecisionService]
                                              │
                   ┌──────────────────────────┴──────────────────────────┐
                   ▼                                                     ▼
     [evaluate_farmer_plot]                                  [evaluate_location_events]
    - Official Alerts (CAP)                                 - Official Alerts (CAP)
    - Chemical Spraying Window                              - Heavy Rainfall (>=35.5 mm)
    - Irrigation Water Balance                              - Extreme Heat (>=40.0°C)
    - Harvest Window Scanning                               - High Wind Squall (>=35.0 km/h)
    - Sowing / Fieldwork Risk                                            │
                   │                                                     │
                   └──────────────────────────┬──────────────────────────┘
                                              │
                                              ▼
                              [EventDeduplicationRegistry]
                               - SHA-256 stable key hashing
                               - Meaningful state-change detection
                               - 6h cooldown window suppression
                               - Critical/High escalation bypass
                                              │
                         ┌────────────────────┴────────────────────┐
                         │                                         │
                 [State Unchanged /                       [Meaningful Change /
                  Cooldown Active]                         Escalation Detected]
                         │                                         │
                         ▼                                         ▼
                     [SUPPRESSED]                      [WeatherDecisionEvent Generated]
                                                                   │
                                                ┌──────────────────┴──────────────────┐
                                                ▼                                     ▼
                                      [Optional LLM Bridge]               [NotificationDeliveryService]
                                      - Gemma conversational               - Decoupled outbox dispatch
                                        explanation                        - Transport failure containment
                                      - Zero verdict mutation             - Delivery state tracking
```

---

## 5. Event Model

The deterministic event model is defined in `app/proactive/models.py`:

```python
class WeatherDecisionEvent(BaseModel):
    event_id: str                      # Unique traceable event identifier (e.g., evt_50ecb845046f)
    user_id: str                       # Target user or registered farmer identifier
    plot_id: Optional[str]             # Registered plot identifier (None for general location events)
    plot_name: Optional[str]           # Human-readable plot label
    crop_name: Optional[str]           # Agronomic crop evaluated (e.g., Wheat, Cotton)
    event_type: WeatherDecisionEventType # One of 10 supported deterministic event types
    severity: EventSeverity            # CRITICAL, HIGH, MODERATE, LOW, INFO
    location: Dict[str, Any]           # Geo coordinates and administrative hierarchy
    operation: Optional[str]           # farm_safety, chemical_spraying, irrigation, harvesting, travel
    verdict: DecisionOutcome           # GO, POSTPONE, NO_GO, PROCEED_WITH_CAUTION
    recommended_action: str            # Direct, unambiguous operational command
    action_window: Optional[Dict[str, Any]] # Forward start/end timestamps when valid
    confidence: ConfidenceLevel        # HIGH, MEDIUM, LOW
    uncertainty: Dict[str, Any]        # Explicit limitations & mandatory disclaimers
    why: List[str]                     # Verified bulleted evidence ledger
    evidence: Dict[str, Any]           # Numerical measurements & threshold records
    provenance: Dict[str, Any]         # Data sources, retrieval timestamps, algorithms
    created_at: str                    # ISO 8601 creation timestamp
    valid_from: str                    # ISO 8601 operational validity start
    valid_until: str                  # ISO 8601 operational validity expiration
    dedup_key: str                     # Deterministic SHA-256 state hash
    delivery_status: EventDeliveryStatus # NEW, DELIVERED, ACKNOWLEDGED, EXPIRED, SUPPRESSED
    explanation: Optional[str]         # Optional localized narrative from Gemma
```

---

## 6. Event Generation

Events are evaluated deterministically in `ProactiveDecisionService` across two operational entrypoints:
1. `evaluate_farmer_plot(plot, preferences)`: Evaluates plot geometry against official CAP polygons, FAO-56 irrigation balance, spray suitability, harvest windows, and fieldwork soil trafficability.
2. `evaluate_location_events(latitude, longitude, location_name, preferences)`: Evaluates outdoor safety hazards for arbitrary general coordinates across official alerts, heatwaves, heavy rain, and high wind.

Each evaluation produces a structured event only if verified physical thresholds are breached.

---

## 7. Change Detection

Change detection tracks the previous operational verdict and severity for each entity/operation pair in `EventDeduplicationRegistry`:
- **Meaningful Transition:** If a plot's spray status transitions from $GO \to POSTPONE$, the state change is recognized immediately.
- **Identical State:** If a plot is evaluated again with the identical verdict ($GO \to GO$) or identical official alert, it is classified as unchanged.
- **Window Evaporation:** If a safe window was active, but subsequent forecast rainfall eliminates the window, an event is emitted warning the farmer of the closure.

---

## 8. Anti-Spam & Deterministic Deduplication

Deduplication in `app/proactive/deduplication.py` enforces three layers of defense against notification fatigue:

1. **SHA-256 Stable Key Generation:**
   $$\text{dedup\_key} = \text{SHA256}(\text{user\_id} \mid \text{entity} \mid \text{event\_type} \mid \text{operation} \mid \text{verdict} \mid \text{severity} \mid \text{hazard})[:24]$$
2. **Cooldown Enforcement:** Identical events are suppressed for a configurable window (default: 6 hours, 21,600 seconds).
3. **Escalation Bypass:** If severity escalates (e.g. Yellow $\to$ Orange or Orange $\to$ Red), the cooldown is bypassed immediately to ensure critical safety warnings are never suppressed.

---

## 9. Severity Hierarchy

Severity is assigned deterministically and adheres strictly to official authority:

| Event Severity | Trigger Conditions | Overridable by LLM? |
| :--- | :--- | :--- |
| **CRITICAL** | Official **Red Alert** inside perimeter, extreme immediate life/crop hazard. | **NO** (Strictly Immutable) |
| **HIGH** | Official **Orange Alert**, heavy rainfall $\ge 64.5\text{ mm}$, destructive winds $\ge 50\text{ km/h}$, spray $NO\_GO$. | **NO** |
| **MODERATE** | Official **Yellow Alert**, spray $POSTPONE$, irrigation needed, heat $\ge 40^\circ\text{C}$, harvest postponement. | **NO** |
| **LOW** | Operations favorable ($GO$), normal irrigation schedule, wind caution. | **NO** |
| **INFO** | Routine bulletins, informational weather summaries. | **NO** |

---

## 10. Farmer Proactive Intelligence

For registered plots, the engine continuously assesses:
- **Official Warning Containment:** Spatial verification (`ST_Covers`) of plot centroid in NDMA Sachet CAP polygons. Red/Orange alerts enforce immediate $NO\_GO$ for farm safety.
- **Chemical Spraying Suitability:** Evaluated using wind $\le 15\text{ km/h}$, rain chance $\le 30\%$, and 4-hour post-spray dry spell. Emits `SPRAY_WINDOW_CHANGE`.
- **FAO-56 Irrigation Balance:** Combines reference $ET_0$, crop coefficient $K_c$, and 48-hour forecast precipitation. Emits `IRRIGATION_CHANGE` when water balance transitions to $IRRIGATE\_NOW$ or $WAIT\_FOR\_RAIN$.
- **Harvest Feasibility:** Scans 24-hour rainfall ($>0.0\text{ mm}$ postpones harvest to avoid grain shattering and mold). Emits `HARVEST_WINDOW_CHANGE`.
- **Sowing & Fieldwork:** Evaluates soil workability based on precipitation. Emits `FIELD_WORK_RISK`.
- **Mandatory Caveats Preserved:**
  - *"Soil moisture status unavailable; recommendation is based on rainfall and forecast conditions."*
  - *"Default crop stage assumed; adjust for local maturity."*

---

## 11. General User Proactive Intelligence

General user coordinate evaluation covers outdoor safety hazards:
- **Approaching Official CAP Alerts:** Spatial exposure determination inside district or polygon.
- **Heavy Rainfall Risk (`HEAVY_RAIN_RISK`):** Total rain $\ge 35.5\text{ mm}$ (IMD Moderate-to-Heavy threshold) or $\ge 64.5\text{ mm}$ (Heavy Rainfall threshold).
- **Extreme Heat Risk (`HEAT_RISK`):** Synoptic temperature $\ge 40.0^\circ\text{C}$ (Plains heatwave criterion).
- **High Wind Risk (`HIGH_WIND_RISK`):** Sustained wind speeds $\ge 35.0\text{ km/h}$ threatening loose outdoor structures and high-profile vehicles.

---

## 12. Notification Delivery Decoupling

The notification architecture separates **decision event creation** from **delivery dispatch**:
- `NotificationDeliveryService` defines the transport boundary.
- `InMemoryNotificationDeliveryService` maintains a per-user outbox with simulated delivery status (`DELIVERED` vs `FAILED`).
- **Transport Fault Isolation:** If push notifications or network connections fail, the generated `WeatherDecisionEvent` remains intact, verified, and accessible via database queries and REST APIs.

---

## 13. Android Integration

The Android application interacts with the proactive engine via clean REST contracts:
- `GET /api/v1/proactive/events/{user_id}`: Retrieves all proactive decisions for the user's registered plots or location.
- `POST /api/v1/proactive/events/{event_id}/acknowledge`: Clears the proactive badge once seen by the farmer.
- `GET /api/v1/proactive/notifications/{user_id}`: Fetches pending notifications for the Android system tray.

Android performs **zero meteorological calculations**; it functions strictly as a high-fidelity presentation layer.

---

## 14. LLM Role & Offline Resilience

Gemma/LLM integration is strictly governed by `_attach_explanation`:
- The LLM receives the verified deterministic verdict, operation, recommended action, and why ledger.
- It produces a friendly, conversational explanation in the user's preferred Indian language.
- **Contradiction Barrier:** The LLM cannot alter `verdict`, `severity`, `recommended_action`, `why`, `evidence`, or `provenance`.
- If Ollama is offline, unreachable, or times out, the system seamlessly returns the deterministic action text without degradation.

---

## 15. REST API Specifications

Mounted under `/api/v1/proactive`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/proactive/evaluate/farmer/{user_id}` | Triggers proactive evaluation across all registered plots for a farmer. |
| `POST` | `/api/v1/proactive/evaluate/location` | Triggers proactive evaluation for arbitrary geographic coordinates. |
| `GET` | `/api/v1/proactive/events/{user_id}` | Queries all active and historical proactive events for a user. |
| `POST` | `/api/v1/proactive/events/{event_id}/acknowledge` | Acknowledges an event, marking it as viewed. |
| `GET` | `/api/v1/proactive/notifications/{user_id}` | Queries decoupled notification outbox for the user. |

---

## 16. Security, Safety, and Quality Boundaries

1. **Official Alert Immutability:** NDMA Sachet CAP warnings are immutable and strictly authoritative.
2. **Deterministic Precedence:** Mathematical agronomic models cannot be influenced or modified by prompts.
3. **Spatial Precision:** Point-in-polygon ray casting confirms whether plots are inside warning perimeters.
4. **Data Isolation:** User and plot queries are scoped strictly by authenticated `user_id`.

---

## 17. Automated Verification & Test Results

### Phase 8 Test Suite (`tests/test_phase8_proactive_events.py`)

Comprehensive suite covering 23 test scenarios:
1. `test_no_meaningful_change_no_event`: No state transition yields zero events.
2. `test_go_to_postpone_triggers_event`: Favorable to postponing triggers event.
3. `test_postpone_to_go_triggers_event`: Postponed to favorable triggers window event.
4. `test_new_official_red_alert_triggers_critical_event`: Official Red alert inside plot triggers CRITICAL event.
5. `test_existing_identical_red_alert_deduplicated`: Unchanged active alert is deduplicated.
6. `test_alert_outside_plot_no_false_event`: Distant alert does not create false positive.
7. `test_unknown_spatial_state_no_fabricated_containment`: Unmapped geometry flags UNKNOWN without fabrication.
8. `test_irrigation_decision_change_triggers_event`: Soil moisture deficit triggers irrigation event.
9. `test_spray_window_change_triggers_event`: Spray wind/rain hazard triggers event.
10. `test_harvest_window_change_triggers_event`: Approaching rain triggers harvest postponement.
11. `test_field_work_risk_change_triggers_event`: Heavy 48h rain triggers fieldwork hazard event.
12. `test_severe_heat_event_generated`: High temperature ($\ge 40^\circ\text{C}$) triggers heat risk.
13. `test_heavy_rainfall_event_generated`: Heavy precipitation ($\ge 35.5\text{ mm}$) triggers rain hazard.
14. `test_high_wind_event_generated`: Gale-force wind ($\ge 35\text{ km/h}$) triggers structural risk.
15. `test_disclaimers_preserved`: Mandatory unmeasured soil and crop stage disclaimers preserved.
16. `test_missing_evidence_no_fabricated_event`: Incomplete bundle does not hallucinate events.
17. `test_missing_llm_deterministic_event_still_works`: Full engine works offline without Ollama.
18. `test_llm_contradiction_deterministic_result_retained`: Contradictory LLM attempts are overridden.
19. `test_provenance_and_official_authority_preserved`: Provenance metadata intact on all outputs.
20. `test_duplicate_event_suppression_cooldown`: 6-hour deduplication suppresses spam.
21. `test_event_expiration_lifecycle`: Expiration timestamps properly delimit event lifetime.
22. `test_notification_delivery_failure_does_not_destroy_event`: Transport drops preserve verified events.
23. `test_api_proactive_endpoints`: End-to-end FastAPI endpoint validation.

**Result: 23 passed in 9.23s.**

### Full Regression Test Suite

- Phase 7 Farmer Registry: 2 passed.
- Phase 7 Alert Pipeline: 1 passed.
- USP Phase 1 Decisions: 8 passed.
- USP Phase 2 Action Window: 10 passed.
- USP Phase 3 Alert Impact: 10 passed.
- USP Phase 4a Explanation Bridge: 9 passed, 2 live Gemma offline skipped.
- Climate Intelligence: 20 passed.
- Farmer Intelligence: 28 passed, 1 live Gemma offline skipped.

**Regression Result: 88 passed, 3 skipped in 87.65s.**  
**Android Unit Tests (`./gradlew.bat testDebugUnitTest`): BUILD SUCCESSFUL (26 tasks up to date).**

---

## 18. Known Limitations

1. **Push Transport Implementation:** The current production deployment provides an in-memory / database notification queue; live FCM/APNS credentials must be provisioned for background mobile push tokens in production staging.
2. **WRF High-Resolution Grids:** WRF 3 km remains unconfigured as documented; GFS 0.25° NWP provides authoritative synoptic forecasts.
3. **In-situ Soil Moisture Sensors:** Physical IoT probe data is unconfigured; deterministic FAO-56 atmospheric balance is applied with explicit disclaimers.

---

## 19. Future Work (Post-Phase 8)

1. Provision FCM push credentials for background system-tray notification broadcasts.
2. Support custom farmer operational preferences (e.g., custom spray drift chemical tolerance thresholds).
3. Connect live multi-plot geo-fencing for mobile GPS background tracking.

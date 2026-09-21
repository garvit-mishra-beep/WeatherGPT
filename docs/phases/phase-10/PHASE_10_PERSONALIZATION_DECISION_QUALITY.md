# PHASE 10 — PERSONALIZATION, DECISION QUALITY & ADAPTIVE WEATHER INTELLIGENCE

**System:** Vayubodhak (WeatherGPT)  
**Status:** IMPLEMENTED & VERIFIED  
**Authoritative Reference:** `AGENTS.md`  

---

## 1. Objective

Phase 10 builds a deterministic, auditable personalization and decision-quality layer for Vayubodhak. Rather than treating AI as an opaque black box that "trains itself," the system learns from verified outcomes and user preferences in a strictly controlled manner so that recommendations become:
- More relevant,
- Better prioritized,
- Better timed,
- Less repetitive,
- Fully personalized, and
- Measurable against actual real-world outcomes.

---

## 2. Core Architecture & The 6 Separated Categories

The fundamental architectural invariant is the strict separation of six distinct data domains:

```
        ┌─────────────────────────────────────────────────────────┐
        │ 1. WEATHER TRUTH                                        │
        │ Physical observations, GFS/ECMWF NWP, CAP alerts        │
        └───────────────────────────┬─────────────────────────────┘
                                    │
                                    ▼
        ┌─────────────────────────────────────────────────────────┐
        │ 2. DETERMINISTIC DECISION                               │
        │ NirnayCard, verdicts (GO, NO_GO), action windows        │
        └─────────────┬─────────────────────────────┬─────────────┘
                      │                             │
                      ▼                             ▼
        ┌───────────────────────────┐ ┌───────────────────────────┐
        │ 3. USER PREFERENCE        │ │ 4. USER ACTION            │
        │ Language, severity, quiet │ │ Viewed, acknowledged,     │
        │ hours, crop priorities    │ │ followed, postponed       │
        └─────────────┬─────────────┘ └─────────────┬─────────────┘
                      │ (tie-breaks, filters)       │
                      ▼                             ▼
        ┌───────────────────────────┐ ┌───────────────────────────┐
        │ 5. OBSERVED OUTCOME       │ │ 6. MODEL/DECISION QUALITY │
        │ Spraying completed,       │ │ Forecast MAE, hit/miss,   │
        │ irrigation completed      │ │ decision adherence rate   │
        └───────────────────────────┘ └───────────────────────────┘
```

### The 6 Distinct Categories:
1. **Weather Truth:** Measured physical observations, numerical models, official CAP polygons. Never mutated, predicted by LLMs, or fabricated.
2. **Deterministic Decision:** Authoritative verdicts (`GO`, `NO_GO`, `POSTPONE`, `PROCEED_WITH_CAUTION`), `NirnayCard`s, and `WeatherDecisionEvent`s calculated strictly via deterministic engines.
3. **User Preference:** User configuration (language, minimum severity, quiet hours, crop operation priority). Influences delivery, ranking, filtering, and presentation. **Never** influences weather values, official alert severity, or safety thresholds.
4. **User Action:** Behavioral interactions (`VIEWED`, `ACKNOWLEDGED`, `DISMISSED`, `FOLLOWED`, `POSTPONED`, `MARKED_COMPLETED`, `IGNORED`). Crucially: $\text{ACKNOWLEDGED} \neq \text{ACTION\_COMPLETED}$.
5. **Observed Outcome:** Explicit user-reported or verified system outcomes (e.g. `SPRAYING_COMPLETED`, `SPRAYING_POSTPONED`, `IRRIGATION_COMPLETED`, `ALERT_USEFUL`). Never inferred merely from a notification opening.
6. **Model/Decision Quality:**
   - **Forecast Accuracy:** Paired forecast vs verified observation at the same location/time (temperature MAE, rainfall error, rain hit/miss, wind error). Missing observations produce an explicit `UNAVAILABLE` state.
   - **Decision Utility:** Operational adherence (`ACTION_ALIGNED`, `ACTION_DEVIATED`, `UNREPORTED`). Kept strictly separate from forecast accuracy.
   - **Notification Utility:** Monotonic counts and ratios of delivered, viewed, acknowledged, and expired events.

---

## 3. Personalization Model (`UserPreferences`)

User preferences govern user experience without corrupting meteorological truth:
- `user_id`: Target farmer/user identity.
- `preferred_language`: English, Hindi, Marathi, Gujarati, Bengali.
- `min_severity`: Notification filter threshold (`CRITICAL`, `HIGH`, `MODERATE`, `LOW`).
- `proactive_enabled`: Master toggle for proactive recommendations.
- `farmer_alerts_enabled`: Enable agricultural operation events.
- `official_warnings_only`: Suppress non-official advisory events.
- `preferred_alert_categories`: Prioritized categories for relevance tie-breaking (e.g. rainfall, wind, heat, pest).
- `operation_priorities`: Farmer operation priority order (e.g. spraying, irrigation, harvest).
- `preferred_notification_timing`: Morning (06:00), evening (18:00), or immediate.
- `preferred_units`: Temperature (°C/°F), wind speed (km/h, m/s), rain (mm).
- `explanation_detail`: Concise, standard, or detailed.
- `quiet_hours`: Local quiet hours window (e.g. 22:00 to 06:00).

---

## 4. Decision History (`decision_history`)

Historical decisions and proactive events are persisted as auditable, immutable records:
- Preserves `decision_id`, `event_id`, `user_id`, `plot_id`, `timestamp`, `question`, `verdict`, `severity`, `recommended_action`, `location`, `operation`, `evidence_snapshot`, `uncertainty`, `provenance`, `action_window`, `official_alert_id`, `official_warning_level`.
- **Immutability:** Historical records are never modified when new forecasts arrive. Past advice remains auditable for liability and quality analysis.

---

## 5. User Action Tracking (`user_action_tracking`)

Logs behavioral interaction separate from operational outcomes:
- Actions: `VIEWED`, `ACKNOWLEDGED`, `DISMISSED`, `FOLLOWED`, `POSTPONED`, `MARKED_COMPLETED`, `IGNORED`.
- Invariant: Acknowledging a notification simply registers awareness. It does **not** signify that the recommended action was taken in the field.

---

## 6. Outcome Capture (`decision_outcomes`)

Explicit recording of what actually happened on the farm:
- Farmer outcomes: `SPRAYING_COMPLETED`, `SPRAYING_POSTPONED`, `IRRIGATION_COMPLETED`, `HARVEST_COMPLETED`, `FIELD_WORK_POSTPONED`.
- General outcomes: `ALERT_USEFUL`, `ALERT_NOT_USEFUL`, `WEATHER_MATCHED_EXPECTATION`, `WEATHER_DIFFERED_FROM_EXPECTATION`.
- Unknown state: Decisions without user reports evaluate strictly to `UNKNOWN` / `UNREPORTED`. Outcomes are never fabricated.

---

## 7. Weather Forecast Verification (`DeterministicForecastVerificationEngine`)

Pairwise comparison between deterministic forecasts and later verified observations at the same location and time:
- **Temperature Error:** $T_{\text{forecast}} - T_{\text{observed}}$ (°C), Mean Absolute Error (MAE), Mean Bias.
- **Rainfall Error:** $R_{\text{forecast}} - R_{\text{observed}}$ (mm), Absolute Error.
- **Rain Occurrence Contingency:** Standard $\ge 0.5\text{ mm}$ meteorological threshold:
  - `HIT`: Forecast $\ge 0.5\text{ mm}$, Observed $\ge 0.5\text{ mm}$.
  - `MISS`: Forecast $< 0.5\text{ mm}$, Observed $\ge 0.5\text{ mm}$.
  - `FALSE_ALARM`: Forecast $\ge 0.5\text{ mm}$, Observed $< 0.5\text{ mm}$.
  - `CORRECT_NEGATIVE`: Forecast $< 0.5\text{ mm}$, Observed $< 0.5\text{ mm}$.
  - Rain Accuracy: $\frac{\text{HIT} + \text{CORRECT\_NEGATIVE}}{\text{Total}}$.
- **Wind Speed Error:** $W_{\text{forecast}} - W_{\text{observed}}$ (km/h), Wind MAE.
- **Timing Error:** Difference between forecast hazard onset and observed hazard onset.
- **Data Honesty:** If observations are missing, returns status `UNAVAILABLE` with `None` error metrics. Never fabricates observations.

---

## 8. Decision Utility (`DecisionUtilityEngine`)

Evaluates whether deterministic recommendations were followed:
- `ACTION_ALIGNED`:
  - `NO_GO` / `POSTPONE` $\to$ User reported `SPRAYING_POSTPONED` or `FIELD_WORK_POSTPONED`.
  - `GO` $\to$ User reported `SPRAYING_COMPLETED` or `IRRIGATION_COMPLETED`.
- `ACTION_DEVIATED`:
  - `NO_GO` $\to$ User reported `SPRAYING_COMPLETED`.
  - `GO` $\to$ User reported postponed due to non-weather reasons.
- `UNREPORTED`: No user feedback received.
- **Independence:** Decision adherence measures farmer cooperation with guidance; it does **not** measure or imply weather forecast correctness.

---

## 9. Personalized Prioritization (`DeterministicPrioritizationEngine`)

Prioritizes events for the "Today for You" surface using an auditable, deterministic formula:

$$\text{PriorityScore} = S_{\text{severity}} + I_{\text{immediacy}} + A_{\text{actionability}} + R_{\text{user\_relevance}}$$

### Scoring Components:
1. **Severity ($S$):**
   - `CRITICAL` (Official Red alert / severe hazard) $= 1000.0$.
   - `HIGH` (Official Orange alert / high risk) $= 500.0$.
   - `MODERATE` $= 200.0$.
   - `LOW` $= 50.0$.
   - `INFO` $= 10.0$.
2. **Immediacy ($I$):** Active now $= 50.0$; $\le 3\text{h} = 40.0$; $\le 6\text{h} = 30.0$; $\le 12\text{h} = 20.0$; $> 12\text{h} = 10.0$.
3. **Actionability ($A$):** `NO_GO` / `POSTPONE` $= 30.0$; `GO` $= 25.0$; `PROCEED_WITH_CAUTION` $= 20.0$; `MONITOR` $= 10.0$.
4. **User Relevance ($R$):** Operation priority match (1st $= 20.0$, 2nd $= 15.0$, 3rd $= 10.0$); alert category match $= 10.0$.

### Absolute Invariant:
Critical official alerts always score $\ge 1000.0$, guaranteeing they rank #1 regardless of user preferences.

---

## 10. Farmer Personalization

Uses verified farmer context:
- `crop_name`, `area_acres`, `centroid_lat`, `centroid_lon` from registered plots.
- Optional fields (`crop_stage`, `soil_type`, `irrigation_method`, `sowing_date`).
- Unsupplied fields remain strictly unknown.

---

## 11. Agronomic Safety Boundaries

- **Threshold Immutability:** User feedback (e.g. "spraying is fine at 20 km/h") can customize user ranking and presentation, but can **never** alter scientific agronomic thresholds (e.g. 15 km/h spray wind limit, 2 mm wash-off limit).
- **Mandatory Disclaimers:** All personalized dashboards preserve:
  - Soil moisture in-situ verification disclaimers.
  - Crop growth stage field scouting disclaimers.
  - Official warning authority disclaimers.

---

## 12. Privacy & Data Minimization

- Scoped strictly to decision relevance and auditability.
- Multi-tenant user data isolation: all history, action, and preference queries filter by `user_id`.
- Zero credentials, passwords, or API secrets stored or logged.

---

## 13. REST APIs (`/api/v1/personalization`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/personalization/{user_id}/preferences` | Fetch persistent user preferences. |
| `POST` | `/api/v1/personalization/preferences` | Upsert user preferences. |
| `GET` | `/api/v1/personalization/{user_id}/today` | Get prioritized "Today for You" dashboard. |
| `POST` | `/api/v1/personalization/events/{event_id}/action` | Record explicit user interaction. |
| `POST` | `/api/v1/personalization/decisions/{decision_id}/outcome` | Record explicit operational outcome. |
| `GET` | `/api/v1/personalization/decisions/{user_id}/history` | Fetch auditable decision history. |
| `GET` | `/api/v1/personalization/quality/{location_or_user}` | Fetch forecast accuracy & utility metrics. |

---

## 14. Database Migrations

- Migration: `app/db/migrations/versions/0005_personalization_decision_quality.py`.
- Tables created:
  1. `user_preferences_store`: Persistent user configuration.
  2. `decision_history`: Immutable decision audit log with B-Tree indexes.
  3. `user_action_tracking`: User interaction tracking log.
  4. `decision_outcomes`: Explicit real-world outcome log.
  5. `forecast_verifications`: Paired forecast vs observation verification table.

---

## 15. Android Integration

- Presentation-only: The Android client displays the prioritized "Today for You" surface rendered by the backend.
- Lightweight Feedback UI: Useful / Not Useful, Followed / Postponed, Dismiss. All feedback is non-blocking.

---

## 16. LLM Role & Independence

- **Strict Isolation:** LLM/Gemma is not in the decision, verification, or ranking loop.
- **Offline Resilience:** All ranking, preference, history, and verification features operate 100% deterministically when LLMs are offline.
- **Explanation Only:** When available, Gemma only provides natural-language summaries of verified deterministic outputs.

---

## 17. Testing & Verification

Comprehensive test suite implemented in `tests/test_phase10_personalization_quality.py`:

| # | Scenario | Result |
| :--- | :--- | :--- |
| 1 | Preference changes notification filtering | **PASS** |
| 2 | Preference cannot alter severity | **PASS** |
| 3 | Preference cannot alter safety threshold | **PASS** |
| 4 | Critical alert always ranks first | **PASS** |
| 5 | Decision history persists | **PASS** |
| 6 | Historical decision remains immutable | **PASS** |
| 7 | Acknowledged $\neq$ completed | **PASS** |
| 8 | User outcome recorded explicitly | **PASS** |
| 9 | Missing outcome remains unknown | **PASS** |
| 10 | Forecast verification with valid observation | **PASS** |
| 11 | Missing observation $\to$ unavailable | **PASS** |
| 12 | Temperature MAE calculation | **PASS** |
| 13 | Rain occurrence verification (contingency table) | **PASS** |
| 14 | Timing error calculation | **PASS** |
| 15 | Decision adherence separated from forecast accuracy | **PASS** |
| 16 | Personalized ranking formula | **PASS** |
| 17 | User preference tie-breaking | **PASS** |
| 18 | Missing farmer context handling | **PASS** |
| 19 | Soil disclaimer preserved | **PASS** |
| 20 | Crop-stage disclaimer preserved | **PASS** |
| 21 | No fabricated outcomes | **PASS** |
| 22 | No fabricated weather | **PASS** |
| 23 | LLM unavailable resilience | **PASS** |
| 24 | LLM contradiction protection | **PASS** |
| 25 | Provenance preserved | **PASS** |
| 26 | Official alert authority preserved | **PASS** |
| 27 | User data isolation (privacy) | **PASS** |
| 28 | Duplicate action handling | **PASS** |
| 29 | Historical audit trail completeness | **PASS** |
| 30 | API schema validation | **PASS** |

**Summary:** `30 passed in 8.06s`.

---

## 18. Regression Test Results

- **Phase 10 Test Suite:** `tests/test_phase10_personalization_quality.py` $\to$ **30 passed in 8.06s** (100%).
- **Phase 9 Push Delivery Suite:** `tests/test_phase9_push_delivery.py` $\to$ **24 passed in 8.51s** (100%).
- **Phase 8 Proactive Events Suite:** `tests/test_phase8_proactive_events.py` $\to$ **23 passed in 9.57s** (100%).
- **Phase 1–7 Regression Suite:** 8 test files $\to$ **88 passed, 3 skipped in 86.88s** (100% green).
- **Android Unit Test Suite:** `.\gradlew.bat testDebugUnitTest` $\to$ **BUILD SUCCESSFUL in 1s** (26 tasks up to date, 0 failures).

---

## 19. Known Limitations

1. **In-Situ Verification:** In the absence of IoT soil sensors, soil moisture verification relies on surface observations and FAO-56 estimates.
2. **Outcome Reporting:** Outcome capture requires voluntary farmer input in the application interface.

---

## 20. Production Readiness Assessment

- **Personalization:** Ready. Deterministic, transparent, and auditable.
- **Safety:** Uncompromised. Weather truth, official alert levels, and agronomic thresholds remain immutable.
- **Auditability:** Complete. Historical decisions preserve inputs, rules, calculations, and provenance snapshots.
- **Quality Metrics:** Ready. Statistical verification engine operates strictly on real paired observations without data fabrication.

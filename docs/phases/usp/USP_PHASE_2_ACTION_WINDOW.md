# Vayubodhak USP Phase 2 — Action Window Engine

## 1. Objective

Phase 2 upgrades the Vayubodhak decision intelligence architecture from reactive negative advisories (*"Do not spray tonight"*) to affirmative, operational scheduling:

> **"Don't just tell me what NOT to do. Tell me WHEN I SHOULD DO IT."**

When an operational task (such as chemical spraying) is postponed due to adverse real-time conditions (e.g. droplet drift or rain wash-off), the **Action Window Engine** deterministically searches the available forward hourly numerical forecast, identifies contiguous periods where all physical constraints remain satisfied, scores each candidate window, and presents the best recommended window alongside alternative fallback windows.

---

## 2. Core USP Pipeline

$$\text{Data} \longrightarrow \text{Evidence} \longrightarrow \text{Intelligence} \longrightarrow \text{Uncertainty} \longrightarrow \text{Decision} \longrightarrow \mathbf{\text{Action Window}} \longrightarrow \text{Proof}$$

* **Data**: NOAA GFS 0.25° NWP prognostic atmospheric grids and multi-provider surface forecasts.
* **Evidence**: Hourly forecast points ($T$, $\text{RH}$, $U_{\text{wind}}$, $P_{\text{prob}}$, $P_{\text{precip}}$) mapped in `EvidenceBundle`.
* **Intelligence**: Canonical agronomic chemical safety thresholds (wind drift limit, rain wash-off threshold, minimum operational duration).
* **Uncertainty**: Transparent assessment of single-model reliance (GFS active, WRF unconfigured).
* **Decision**: Operational verdict (`POSTPONE`, `GO`, `NO_GO`).
* **Action Window**: Forward-scanned, multi-criteria-scored execution intervals (`ActionWindow`).
* **Proof**: Candidate-hour audit trace linking forecast variables to threshold evaluations in `EvidenceLedger`.

---

## 3. Architecture

```text
EvidenceBundle (Hourly Forecast Time-Series)
     │
     ▼
ActionWindowEngine (app/decision/action_window.py)
  ├── 1. Hourly Point Extraction (Wind, Rain Prob, Precipitation, Temperature)
  ├── 2. Canonical Agronomic Constraint Evaluation (evaluate_spray_window)
  ├── 3. Contiguous Passing Hour Streak Accumulation
  ├── 4. Window Boundary Segmentation (Splits on failing hours)
  ├── 5. Minimum Duration Verification (Configurable: >= 2 hours)
  ├── 6. Deterministic Multi-Criteria Window Scoring (0.0 to 100.0)
  └── 7. Best Window & Fallback Ranking
     │
     ▼
NirnayCard (action_window = ActionWindow)
  ├── status: "available" | "unavailable"
  ├── best_window: ActionWindowPeriod (Recommended)
  ├── fallback_windows: List[ActionWindowPeriod]
  ├── why: Enhanced with window timing & physical metrics
  ├── alternatives: Populated with actionable execution hours
  └── EvidenceLedger: Complete candidate-hour evaluation trace
```

---

## 4. Hourly Forecast Evaluation & Canonical Constraints

To prevent threshold divergence or duplicate code, all spray criteria are sourced from canonical constants in [`app/analytics/water_balance.py`](../../../app/analytics/water_balance.py):
* **Wind Drift Safety**: $U_{\text{wind}} \le 15.0\text{ km/h}$ (`SPRAY_MAX_WIND_SPEED_KMH`). Wind speeds above 15 km/h cause chemical droplets to drift away from the crop canopy into non-target zones or evaporate prematurely.
* **Precipitation Probability**: $P_{\text{prob}} \le 30.0\%$ (`SPRAY_MAX_RAIN_PROBABILITY_PCT`). Rain probabilities above 30% indicate elevated risk of convective showers.
* **Precipitation Volume (Wash-off)**: $P_{\text{precip}} \le 0.0\text{ mm}$ (`SPRAY_MAX_POST_RAIN_MM`). Active ingredients are dissolved and washed off foliage into field drainage before absorption.

For every candidate forecast hour $h_i$, the engine evaluates:
$$\text{passed}(h_i) = (\text{wind}_i \le 15.0) \land (\text{rain\_prob}_i \le 30.0) \land (\text{precip}_i \le 0.0)$$

Each evaluation is captured in a `CandidateHourEvaluation` recording exact physical values, pass/fail status, and specific failure reasons.

---

## 5. Window Generation & Operational Sufficiency

1. **Contiguous Grouping**: Consecutive passing hours are aggregated into candidate window periods. Any failing hour immediately terminates the current candidate streak.
2. **Operational Sufficiency vs. Meteorological Validity**:
   - An isolated passing hour (e.g. 1 hour with wind 8 km/h preceded and followed by gale-force winds) is meteorologically calm, but operationally insufficient.
   - Farm chemical application requires mixing, nozzle calibration, field transit, and safe completion margin across plot rows.
   - The engine enforces a configurable `min_spray_window_hours = 2`. Streaks shorter than this threshold are rejected from qualifying as actionable windows.
3. **Interval Representation**:
   - `start_time_iso`: Timestamp of the first passing hour.
   - `end_time_iso`: Completion timestamp of the final passing hour (1 hour past start of last hour).
   - Example: Consecutive valid hours 06:00, 07:00, 08:00, 09:00 yield an interval of `06:00 - 10:00 (4h continuous)`.

---

## 6. Deterministic Multi-Criteria Window Scoring

Qualified candidate windows are scored deterministically on a bounded scale $S \in [0.0, 100.0]$:

$$S = S_{\text{wind}} + S_{\text{rain}} + S_{\text{duration}} + S_{\text{proximity}}$$

| Component | Weight | Mathematical Formula | Physical Justification |
| :--- | :--- | :--- | :--- |
| **Wind Calmness** ($S_{\text{wind}}$) | $40.0$ | $40.0 \times \max\left(0, \frac{15.0 - \overline{U}_{\text{wind}}}{15.0}\right)$ | Calmer air maximizes droplet deposition on target leaves. |
| **Rain Safety** ($S_{\text{rain}}$) | $30.0$ | $30.0 \times \max\left(0, \frac{30.0 - \max(P_{\text{prob}})}{30.0}\right)$ | Lower rain chance prevents wash-off risk. |
| **Window Duration** ($S_{\text{duration}}$) | $20.0$ | $\min(20.0, \text{duration\_hours} \times 5.0)$ | Longer continuous window gives greater operational flexibility. |
| **Proximity Prioritization** ($S_{\text{proximity}}$) | $10.0$ | $\max(0.0, 10.0 - 0.2 \times \text{lead\_hours})$ | Sooner application stops pest reproduction earlier. |

Ties are resolved deterministically by earlier start timestamp.

---

## 7. Best Window & Fallback Selection

- The highest-scoring candidate window is designated as `best_window` (`recommended=True`).
- Remaining candidate windows (up to 3) are populated in `fallback_windows`.
- If no qualified window is found in the forecast horizon:
  - `status = "unavailable"`
  - `best_window = None`
  - `fallback_windows = []`
  - `reason`: Honest, unvarnished physical explanation (e.g. *"No contiguous valid spray window of at least 2 hours exists in the current forecast horizon..."*).

---

## 8. Uncertainty & WRF Honesty Rule

Adhering strictly to meteorological integrity:
* If high-resolution WRF data is unconfigured, the system explicitly confirms:
  ```json
  "uncertainty": {
    "wrf_regional_available": false,
    "statement": "Decision rendered using verified GFS 0.25° / surface synoptic data. WRF regional model is unconfigured and not active; no multi-model divergence is claimed."
  }
  ```
* The statement `"GFS and WRF agree"` is **never output**.

---

## 9. Evidence Traceability & Ledger Audit

Every evaluated candidate hour is captured in `EvidenceLedger`:
1. **Rule Evaluation**: `forward_action_window_search` records the observed window summary and pass/fail satisfaction.
2. **Calculations**: `calculations["action_window_scan"]` records:
   - `total_candidate_hours_scanned`
   - `valid_hours_count`
   - `best_window`: Start time, end time, duration, score, and physical averages.
   - `fallback_windows_count`

---

## 10. Verification & Test Suite

The Action Window Engine is validated by 10 deterministic tests in [`tests/test_usp_phase2_action_window.py`](../../../tests/test_usp_phase2_action_window.py):

| Test Name | Focus | Result |
| :--- | :--- | :--- |
| `test_fixture_a_consecutive_valid_hours` | 4 consecutive valid hours $\to$ Single top window found | **PASSED** |
| `test_fixture_b_high_wind_splits_window` | High wind in middle $\to$ Splits correctly into 2 windows | **PASSED** |
| `test_fixture_c_rain_probability_splits_window` | Rain prob spike $\to$ Splits correctly into 2 windows | **PASSED** |
| `test_fixture_d_rain_volume_break` | Active rain $\to$ Window rejected | **PASSED** |
| `test_fixture_e_no_valid_future_window` | Persistent high winds $\to$ `status: unavailable` reported | **PASSED** |
| `test_fixture_f_multiple_valid_windows_ranking` | Deterministic ranking chooses calmer morning over breezier afternoon | **PASSED** |
| `test_fixture_g_incomplete_forecast` | Empty hourly data $\to$ `status: unavailable`, `confidence: LOW` | **PASSED** |
| `test_minimum_window_operational_sufficiency` | 1-hour isolated spike rejected when `min_hours=2`, accepted when `1` | **PASSED** |
| `test_golden_spray_decision_with_calculated_action_window` | **Golden Test**: Tonight postponed (wind $18.5\text{ km/h}$) $\to$ Recommends tomorrow morning ($06:00 - 10:00$) with ledger trace | **PASSED** |
| `test_api_decisions_with_action_window_fixture` | `POST /api/v1/decisions` contract returns populated `action_window` | **PASSED** |

**Total Backend Suite: 18 passed (8 Phase 1 + 10 Phase 2).**

---

## 11. Android Client Integration (Phase 2 Sprint)

### Architecture & Components
1. **Data Layer DTOs** (`com.weathergpt.data.remote.dto.decision`):
   - `DecisionRequestDto`, `DecisionLocationDto`, `CandidateHourEvaluationDto`, `ActionWindowPeriodDto`, `ActionWindowDto`, `LedgerRuleEvaluationDto`, `EvidenceLedgerDto`, `NirnayCardDto`.
2. **Domain Models** (`com.weathergpt.domain.model.decision`):
   - `DecisionVerdict`, `DecisionSeverity`, `DecisionConfidence`, `CandidateHourEvaluation`, `ActionWindowPeriod`, `ActionWindow`, `LedgerRuleEvaluation`, `EvidenceLedger`, `DecisionUncertainty`, `NirnayCard`.
3. **API Client & Repository**:
   - `WeatherGPTApiService.evaluateDecision`: `@POST("api/v1/decisions")`.
   - `WeatherGPTRepository.evaluateDecision(...)`: Safe network execution returning `Result<NirnayCard>`.
4. **Presentation**:
   - `NirnayCardComposable`: High-fidelity Jetpack Compose component rendering verdict banner, severity badge, best action window metrics card (duration, avg wind, max rain %, rainfall mm, score), fallback window list, unavailable window fallback, honest uncertainty/WRF notice, and expandable "Why this decision?" section with rule ledger rows and candidate hour evaluations.
   - `ChatViewModel` & `ChatScreen`: Operational queries routed to `evaluateDecision` without LLM calls; assistant messages render embedded `NirnayCardComposable`.
   - Quick prompt chips on `ChatScreen` and `HomeScreen` for instant testing.

### Android Verification Results
- **Unit Tests**: 167/167 tests passed (`.\gradlew.bat testDebugUnitTest`, 0 failures, 100% success rate).
  - `DecisionMapperTest`: 2 tests passed (Available & Unavailable action windows).
  - `NirnayCardTest`: 3 tests passed (Model creation, GO/POSTPONE verdicts, fallback windows, unavailable window honesty).
  - `WeatherGPTRepositoryTest`: 10 tests passed (including `evaluateDecision`).
- **APK Build**: `.\gradlew.bat assembleDebug` succeeded cleanly (`app-debug.apk`, 22 MB).
- **Backend Regression**: 18/18 USP tests passed (8 Phase 1 + 10 Phase 2).
- **Physical Device**: Verified via `adb devices` — no physical device currently attached; USB/Wi-Fi deployment ready.

---

## 12. Known Limitations

1. **Cotton/Field Crop Domain Focus**: Phase 2 implements chemical spray constraints for cotton and field crops. Specialized orchard or drone application constraints are reserved for future phases.
2. **Single-Model Reliance**: Driven by GFS 0.25° NWP; multi-model ensemble spread and divergence will be integrated in Phase 3.
3. **Physical Device Testing**: No physical Android handset currently attached via ADB; verified on JVM unit tests and clean Gradle APK compilation.

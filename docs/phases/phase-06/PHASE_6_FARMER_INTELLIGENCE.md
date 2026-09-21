# PHASE 6 — FARMER INTELLIGENCE EXPANSION

**Document:** `docs/PHASE_6_FARMER_INTELLIGENCE.md`  
**System:** Vayubodhak (WeatherGPT)  
**Status:** IMPLEMENTED & VERIFIED  
**Authoritative Architectural Guideline:** `AGENTS.md`  

---

## 1. Executive Summary & Core Philosophy

Vayubodhak adheres strictly to the operational pipeline:

$$\text{Data} \longrightarrow \text{Evidence} \longrightarrow \text{Intelligence} \longrightarrow \text{Uncertainty} \longrightarrow \text{Decision} \longrightarrow \text{Action} \longrightarrow \text{Proof}$$

Phase 6 expands agricultural decision support for Indian farmers by turning verified weather evidence and crop context into deterministic, explainable operational recommendations.

### Critical Invariants
1. **The LLM is strictly an explainer, never the agronomic or weather calculator or decision maker.** Gemma 4:e2b receives the verified deterministic `NirnayCard` and generates conversational explanations.
2. **Zero Fabrication:** The system never invents soil moisture, crop stage, rainfall, crop thresholds, or severe weather warnings.
3. **Mandatory Soil Moisture Disclaimer:** Unmeasured soil moisture triggers the required statement:  
   *"Soil moisture status unavailable; recommendation is based on rainfall and forecast conditions."*
4. **Mandatory Crop Stage Handling:** Unknown crop stage defaults to `crop_stage = "UNKNOWN"` with an explicit disclaimer that advice is based on standard baseline requirements.
5. **Official Alert Priority:** IMD/NDMA CAP official warnings (Red/Orange + Inside) retain absolute override authority over all field operations.

---

## 2. Capabilities Support Matrix

| Operational Domain | Status | Evidence Source | Deterministic Engine |
| :--- | :--- | :--- | :--- |
| **Irrigation Need & Urgency** | **SUPPORTED** | Open-Meteo / GFS $ET_0$, Forecast Rain | FAO-56 Penman-Monteith, Crop Water Balance |
| **Spraying Window** | **SUPPORTED** | Open-Meteo 10m Wind, Pop, Rain Volume | Phase 2 ActionWindowEngine, Spray Evaluator |
| **Harvest Window** | **SUPPORTED** | Hourly Rain, Pop, Wind, Humidity, Alerts | Deterministic Multi-parameter Threshold Matrix |
| **Sowing / Field Work** | **SUPPORTED** | Heavy Rain ($\ge 25\text{ mm}$), Heat, Wind | Deterministic Workability Rules + Soil Caveat |
| **Daily Farm Plan** | **SUPPORTED** | Multi-operation Weather Evidence | Ranked Farm Plan Engine with Evidence Traces |
| **Crop-Weather Risk** | **SUPPORTED** | Heat Anomalies, Dry Spells, Wind, Alerts | Climate Intelligence + Threshold Rules |
| **Crop-Specific Phenology** | **PARTIALLY SUPPORTED** | Static $K_c$ lookup (Wheat, Cotton, Rice, etc.) | If stage missing, defaults to `UNKNOWN` ($K_c=1.0$) |
| **Soil Moisture Dynamics** | **PARTIALLY SUPPORTED** | Rainfall accumulation / proxy only | Explicit disclaimer: unmeasured in situ sensor |
| **Disease / Pest Diagnosis** | **UNAVAILABLE** | None | Strictly rejected; no disease guessing |
| **Chemical Dosage** | **UNAVAILABLE** | None | Strictly rejected; safety boundary enforced |
| **Guaranteed Yield Claims** | **UNAVAILABLE** | None | Strictly rejected; probabilistic weather risk only |

---

## 3. Architecture & Data Flow

```text
                                  Farmer Request
                       (e.g., "Should I harvest tomorrow?")
                                        │
                                        ▼
                                  FarmerContext
                   (crop, crop_stage="UNKNOWN", soil, lat, lon)
                                        │
                                        ▼
                                 EvidenceBundle
                      (Weather, Alerts, Climate Baseline)
                                        │
                                        ▼
                                 FarmerEvidence
               (Weather + Water Balance + Hazards + Uncertainty)
                                        │
                                        ▼
                           Deterministic Decision Engine
            ┌───────────────────────────┼───────────────────────────┐
            ▼                           ▼                           ▼
    evaluate_spray()          evaluate_harvest()           evaluate_sowing()
    (ActionWindowEngine)      (Threshold Evaluator)       (Workability Rules)
            └───────────────────────────┬───────────────────────────┘
                                        ▼
                                   NirnayCard
               (GO / POSTPONE / NO_GO / PROCEED_WITH_CAUTION)
                                        │
                                        ▼
                           Farmer Explanation Bridge
                                (Gemma 4:e2b)
                                        │
                   ┌────────────────────┴────────────────────┐
            Contradiction Detected?                     Success?
                   │                                         │
                   ▼                                         ▼
         Deterministic Fallback                     Natural-Language
              Explanation                              Explanation
```

---

## 4. Farmer Context & Evidence Models

### 4.1 FarmerContext (`app/farmer/models.py`)
Encapsulates all optional operational context provided by the farmer.
```python
class FarmerContext(BaseModel):
    crop: Optional[str] = None
    crop_stage: str = "UNKNOWN"
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    soil_type: Optional[str] = None
    irrigation_method: Optional[str] = None
    field_size: Optional[str] = None
    sowing_date: Optional[str] = None
    last_irrigation: Optional[str] = None
    last_rainfall: Optional[str] = None
    crop_coefficient: Optional[float] = None
    user_notes: Optional[str] = None
```
If `crop_stage` is not specified, it defaults strictly to `"UNKNOWN"`, causing the engine to issue a caveat that crop-specific stage rules were unavailable.

### 4.2 FarmerEvidence (`app/farmer/models.py`)
Preserves structured meteorological, crop, water, hazard, and provenance data:
- `weather`: Temperature, rainfall, rain probability, wind speed, relative humidity, $ET_0$.
- `crop`: Name, stage, resolved crop coefficient ($K_c$), stage-known flag.
- `water`: Forecast rainfall, recent rainfall, water balance deficit, soil disclaimer.
- `hazard`: Official alerts, heatwave flags, high wind flags, heavy rain warnings.
- `climate`: Dry-spell days, temperature anomaly context.
- `provenance`: Provider name, dataset, timestamp, units.
- `uncertainty`: Operational uncertainty factors.

---

## 5. Deterministic Intelligence Engines

### 5.1 Irrigation Intelligence (`evaluate_irrigation_intelligence`)
Reuses the verified FAO-56 Penman-Monteith reference evapotranspiration and `calculate_crop_water_balance`:
- $ET_c = ET_0 \times K_c$
- $\text{Net Deficit} = ET_c - \text{Rainfall}$
- If forecast rainfall $\ge ET_c$:
  - State: `WAIT_FOR_RAIN` $\to$ Decision: `POSTPONE` (Save water and energy).
- If $\text{Net Deficit} > 5.0\text{ mm}$:
  - If heavy rain expected: `WAIT_FOR_RAIN`.
  - Else: `IRRIGATE_SOON` or `IRRIGATE_NOW` $\to$ Decision: `GO`.
- If $\text{Net Deficit} \le 0$:
  - State: `NO_IRRIGATION_NEEDED` $\to$ Decision: `POSTPONE`.

### 5.2 Spray Intelligence (`evaluate_spray_window`)
Reuses Phase 2 `ActionWindowEngine`:
- Maximum permissible wind: $15.0\text{ km/h}$.
- Maximum permissible rain probability: $30\%$.
- Rain volume cutoff: $0.0\text{ mm}$.
- Minimum workable duration: $\ge 2\text{ hours}$.

### 5.3 Harvest Intelligence (`evaluate_harvest_window`)
Evaluates operational weather constraints for grain and fiber harvesting:
- Rainfall threshold: $0.0\text{ mm}$ (Dry condition required).
- Maximum rain probability: $25\%$.
- Maximum surface wind: $25.0\text{ km/h}$.
- Maximum relative humidity: $75\%$.
- Minimum continuous workable window: $\ge 4\text{ hours}$.
- Verdict:
  - Forecast rain $> 0.0\text{ mm}$ $\implies$ `NO_GO` / `UNSUITABLE` (Risk of grain wetting and fungal mold).
  - High wind $> 25\text{ km/h}$ $\implies$ `POSTPONE` (Risk of shattering and machine instability).
  - All conditions met $\implies$ `GO` / `SUITABLE`.

### 5.4 Sowing & Field-Work Intelligence (`evaluate_sowing_fieldwork`)
Evaluates field trafficability and operational safety:
- Heavy rain hazard: $\ge 25.0\text{ mm}$ $\implies$ `NO_GO` / `UNSUITABLE` (Soil saturation, waterlogging, machinery bogging).
- Severe heat hazard: $\ge 42.0^\circ\text{C}$ $\implies$ `POSTPONE` / `MARGINAL` (Worker heat exhaustion, seed desiccation).
- High wind hazard: $\ge 30.0\text{ km/h}$ $\implies$ `POSTPONE`.
- **Soil Moisture Rule:** If no physical soil probe exists, output strictly appends:  
  *"Soil moisture status unavailable; recommendation is based on rainfall and forecast conditions."*

### 5.5 Crop-Weather Risk (`evaluate_crop_weather_risk`)
Synthesizes extreme weather stress:
- Heat anomaly $\ge +4.5^\circ\text{C}$: `CRITICAL` heat stress.
- Heat anomaly $\ge +3.0^\circ\text{C}$: `HIGH` heat stress.
- Prolonged dry spell $\ge 14\text{ days}$: `HIGH` moisture stress.
- 24h rainfall $\ge 50\text{ mm}$: `HIGH` waterlogging hazard.
- Surface gusts $\ge 40\text{ km/h}$: `HIGH` crop lodging hazard.
- **Safety Boundary:** Strictly evaluates weather stress. Never diagnoses fungal/bacterial diseases without physical sensor/lab verification.

### 5.6 Daily Farm Action Plan (`generate_daily_farm_plan`)
Evaluates all operations simultaneously and outputs a prioritized operational summary:
1. Spraying evaluation.
2. Irrigation evaluation.
3. Field work evaluation.
4. Harvesting evaluation.
Outputs `DailyFarmPlan` containing prioritized items with verdicts, timing, reasons, and supporting evidence.

---

## 6. Official Alert Override Authority

IMD / NDMA Sachet CAP severe weather alerts have absolute priority over all agricultural tasks:
- **Red Alert + Inside District:** Forces `NO_GO` across all field operations (Irrigation, Spraying, Sowing, Harvesting).
- **Orange Alert + Inside District:** Forces `POSTPONE` and suppresses action windows during the active alert period.
- **Alert Reason:** Preserved verbatim from the official authority.

---

## 7. Gemma Explanation Bridge & Safety Guardrails

### 7.1 Farmer Explanation Bridge (`FarmerExplanationBridge`)
System Prompt Mandate:
```text
You are Vayubodhak's Farmer Decision Explanation Assistant.
You explain verified agricultural weather decisions to Indian farmers.
You are NOT the weather-data source, agronomy calculator, or decision maker.
```

### 7.2 Contradiction Guard
The bridge monitors LLM output against the deterministic verdict. If Gemma attempts to suggest an operation when the verdict is `POSTPONE` or `NO_GO`:
- Triggers: `"safe to spray"`, `"go ahead"`, `"can spray"`, `"ideal time to spray"`, `"good time to spray"`, `"safe to harvest"`, `"can irrigate"`, `"good time to harvest"`.
- Action: Discards the LLM response and falls back immediately to the deterministic evidence-backed explanation.
- The deterministic `NirnayCard` verdict remains 100% immutable.

---

## 8. REST API Endpoints

### 8.1 `POST /api/v1/farmer/advisory`
**Request Payload:**
```json
{
  "location": "Nagpur, Maharashtra",
  "latitude": 21.1458,
  "longitude": 79.0882,
  "crop": "Cotton",
  "crop_stage": "UNKNOWN",
  "operation": "spray",
  "soil_type": "Black Cotton Soil",
  "include_explanation": false
}
```

**Response Payload:**
```json
{
  "status": "success",
  "operation": "spray",
  "verdict": "POSTPONE",
  "nirnay_card": {
    "action_id": "act_8e2a1b",
    "verdict": "POSTPONE",
    "recommended_action": "Delay spraying until winds drop below 15 km/h",
    "confidence_score": 0.88,
    "reasons": ["Wind speed 18.5 km/h exceeds safe threshold (15 km/h)"],
    "action_window": {
      "best_window": {
        "start": "2026-09-08T18:00:00Z",
        "end": "2026-09-08T22:00:00Z"
      }
    }
  },
  "farmer_evidence": { ... },
  "explanation": "Spraying is postponed because current wind speed of 18.5 km/h exceeds the maximum safe limit of 15.0 km/h.",
  "soil_disclaimer": "Soil moisture status unavailable; recommendation is based on rainfall and forecast conditions.",
  "crop_stage_disclaimer": "Crop stage unknown; recommendations use baseline standard requirements."
}
```

### 8.2 `POST /api/v1/farmer/plan`
**Request Payload:**
```json
{
  "location": "Ludhiana, Punjab",
  "crop": "Wheat",
  "soil_type": "Loam"
}
```

**Response Payload:**
```json
{
  "location": "Ludhiana, Punjab",
  "crop": "Wheat",
  "date": "2026-09-08",
  "items": [
    {
      "operation": "irrigation",
      "verdict": "POSTPONE",
      "recommended_action": "Delay irrigation; 14.0 mm rainfall expected",
      "reason": "14.0 mm forecast rainfall offsets crop evapotranspiration requirement."
    },
    {
      "operation": "spraying",
      "verdict": "POSTPONE",
      "recommended_action": "Postpone spraying due to rain hazard",
      "reason": "Rainfall probability exceeds 30% safe threshold."
    }
  ],
  "summary": "2 of 4 evaluated operations require postponement or caution due to weather conditions."
}
```

---

## 9. Verification & Test Suite

The Phase 6 implementation was comprehensively verified across unit, integration, and regression suites.

```bash
pytest tests/test_farmer_intelligence.py tests/test_usp_phase1_decisions.py tests/test_usp_phase2_action_window.py tests/test_usp_phase3_alert_impact.py tests/test_usp_phase4a_explanation_bridge.py tests/test_climate_intelligence.py tests/test_farmer_brain.py tests/test_ollama_provider.py -v
```

**Result:**
```text
================== 104 passed, 4 skipped in 81.40s (0:01:21) ==================
```

### Android Unit Tests
```bash
./gradlew testDebugUnitTest
```
**Result:**
```text
BUILD SUCCESSFUL in 1s
26 actionable tasks: 26 up-to-date
```

---

## 10. Known Boundaries & Limitations

1. **Unmeasured Soil Moisture:** In-situ soil moisture sensor telemetry is currently not integrated into the live feed; proxy rainfall accumulations and explicit disclaimers are used.
2. **Dynamic Crop Phenology Models:** Complex thermal-time (GDD) growth stage simulations require user-specified planting dates; when omitted, the system defaults to `UNKNOWN` stage.
3. **No Direct Pest/Disease Scouting:** Operational advice addresses weather suitability only. Micro-climate pathogen spore germination models are outside current scope.
4. **WRF Mesoscale Model Honesty:** Staging runs without local WRF explicitly report WRF as unavailable and rely on verified GFS 0.25° and Open-Meteo feeds.

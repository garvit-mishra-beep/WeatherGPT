# Domain Brains Layer (`app/brains/`)

## 1. Purpose
Encapsulates domain-specific intelligence, reasoning workflows, tool execution loops, grounding verification, and response synthesis across the four specialized Brains of WeatherGPT.

## 2. The Four Concrete Brains

### 1. General Weather Brain (`GeneralBrain` in `general.py`)
- **Focus:** Everyday consumer forecasts, temperature, precipitation chance, wind speed, official IMD severe weather alerts.
- **Authorized Tools:** `resolve_location`, `get_forecast`.
- **Output:** Synthesizes clear, plain-language summaries and emits `weather_card` visualizations.

### 2. Farmer / Agriculture Brain (`FarmerBrain` in `farmer.py`)
- **Focus:** Agricultural decision support, irrigation scheduling (dual-coefficient water balance), spray suitability windows, crop risk.
- **Authorized Tools:** `calculate_irrigation_advisory`, `get_forecast`, `resolve_location`, `run_risk_analysis`.
- **Output:** Actionable agronomic advisories (`primary_action=IRRIGATE | POSTPONE | SUITABLE`) and `rainfall_irrigation_combo` chart specifications.

### 3. Researcher / Climate Science Brain (`ResearcherBrain` in `researcher.py`)
- **Focus:** Climatological inquiry, multi-decadal historical climate trends, anomaly interpretation, multi-model ensemble divergence (GFS, ECMWF, IMD-GFS).
- **Authorized Tools:** `get_forecast`, `resolve_location`, `run_risk_analysis`.
- **Output:** Scientific trend analysis, confidence indicators, and `line` chart visualizations.

### 4. Analyst / Disaster Risk Brain (`AnalystBrain` in `analyst.py`)
- **Focus:** Spatial hazard-exposure-vulnerability quantification, multi-district risk comparisons, operational mitigation planning.
- **Authorized Tools:** `run_risk_analysis`, `get_forecast`, `resolve_location`.
- **Output:** Operational risk mitigation advisories (`primary_action=WITHHOLD | SUITABLE`) and spatial `map` visualization specifications.

## 3. Important Infrastructure Files
- `base.py`: Abstract `BaseBrain` base class.
- `registry.py`: `BrainRegistry` managing Brain registrations and exports.
- `resolver.py`: `BrainResolver` selecting explicit vs auto-routed Brains.
- `orchestrator.py`: `BrainOrchestrator` coordinating request dispatch and response schema validation.
- `errors.py`: Brain domain error hierarchy.

## 4. Invariants
- Brains do not contain hardcoded meteorological data; all facts are fetched through deterministic tools.
- Output payloads strictly conform to `FinalResponseSchema`.
- Grounding verification is enforced prior to emitting final responses.

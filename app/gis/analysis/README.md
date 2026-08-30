# Deterministic GIS Analysis Engine (`app/gis/analysis/`)

## 1. Purpose
The `app/gis/analysis/` package provides high-performance deterministic risk and spatial impact evaluation:
- Multi-Hazard Characterization & Scoring ($H \in [0.0, 10.0]$)
- PostGIS Spatial Exposure Quantification ($E \in [0.0, 10.0]$, Area $\text{km}^2$, % Overlap)
- Regional Vulnerability Assessment ($V \in [0.0, 10.0]$)
- Operational Impact Evaluation ($I = 0.50 \times H + 0.30 \times E + 0.20 \times V$)
- Compounding Multi-Hazard Interaction Analysis

## 2. Package Architecture
```text
app/gis/analysis/
├── __init__.py                # Package exports (GISAnalysisEngine, types, errors)
├── README.md                  # This documentation
├── types.py                   # Pydantic v2 typed contracts (HazardRecord, ExposureMetrics, ImpactResult, GISAnalysisResult)
├── errors.py                  # Typed error taxonomy (GISAnalysisError, InvalidHazardInputError, etc.)
├── hazards.py                 # Hazard normalization and IMD threshold scoring
├── exposure.py                # Geodesic exposed area and overlap % calculations
├── vulnerability.py           # Urbanization and drainage capacity vulnerability scoring
├── impact.py                  # Composite H x E x V impact calculation and risk classification
├── multi_hazard.py            # Multi-hazard compounding and interaction multipliers
└── engine.py                  # GISAnalysisEngine high-level service boundary
```

## 3. Public APIs & Usage
```python
from app.gis.analysis import (
    GISAnalysisEngine,
    calculate_operational_impact,
    score_rainfall_rate_hazard,
    score_wind_hazard,
    evaluate_multi_hazard_compounding,
)

# 1. Direct Analytical Impact Calculation
impact = calculate_operational_impact(hazard_score=7.5, exposure_score=5.0, vulnerability_score=6.0)
print(f"Impact: {impact.composite_impact_score} ({impact.risk_category.value})")
print(f"Action: {impact.action_priority}")

# 2. Multi-Hazard Compounding
h_rain = score_rainfall_rate_hazard(120.0)  # Heavy Rain
h_wind = score_wind_hazard(60.0)           # Squall
multi_res = evaluate_multi_hazard_compounding([h_rain, h_wind])
print(f"Compound Score: {multi_res.compound_hazard_score} (Multiplier: {multi_res.interaction_multiplier})")

# 3. High-Level Point & Polygon Analysis
engine = GISAnalysisEngine()
res = await engine.analyze_point(latitude=21.17, longitude=72.83, observed_rain_mm=85.0)
print(f"District: {res.district_name}, Impact Score: {res.impact.composite_impact_score}")
```

## 4. Testing
Run the automated test suite:
```powershell
pytest -q
```

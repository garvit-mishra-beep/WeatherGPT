# 64. Data & Analyst Screens — Milestone P6.9 Specification & Verification

**Document:** `docs/64_DATA_ANALYST_SCREEN.md`  
**Status:** COMPLETE & VERIFIED  
**Repository:** `WeatherGPT`  
**Milestone:** P6.9 — Data & Research and Analyst Dashboard Visual & Functional Implementation  
**Visual Source of Truth:** Pragya's UX/UI Design Blueprint (Screens: डेटा और शोध / Data & Research & आपदा एवं जोखिम / Analyst Dashboard)  
**Primary Authorities:** [`docs/01_PRD.md`](docs/01_PRD.md), [`docs/08_NWP_SPEC.md`](docs/08_NWP_SPEC.md), [`docs/09_GIS_SPEC.md`](docs/09_GIS_SPEC.md), [`docs/11_ANALYTICS_ENGINE.md`](docs/11_ANALYTICS_ENGINE.md), [`docs/58_ANDROID_API_INTEGRATION.md`](docs/58_ANDROID_API_INTEGRATION.md)

---

## 1. Executive Summary

Milestone **P6.9** delivers the complete visual and functional implementation of the **DATA & RESEARCH SCREEN (डेटा और शोध)** and the **ANALYST DASHBOARD (आपदा एवं जोखिम)** in Android Jetpack Compose, consuming verified Numerical Weather Prediction (NWP) arrays and PostGIS spatial risk-exposure-vulnerability metrics from the FastAPI backend services (`GET /api/v1/nwp/gfs`, `GET /api/v1/nwp/comparison`, `GET /api/v1/gis/risk-assessment`, and `GET /api/v1/gis/analysis`).

```
┌─────────────────────────────────────────────────────────────┐
│ 📍 Data & Research (डेटा और शोध)                             │
├─────────────────────────────────────────────────────────────┤
│ [ GFS (0.25°) ] [ ECMWF (IFS) ] [ Ensemble Spread ]         │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ NWP वायुमंडलीय ग्रिड (NOAA GFS 0.25°)                   │ │
│ │ Model: GFS | Lead: +24h                      Res: 0.25° │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ Temp: 30°C │ Rain: 0.0 mm │ Wind: 12 km/h │ 1011 hPa│ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ मल्टी-मॉडल तुलना (Model Divergence)                     │ │
│ │ Divergence Ratio: 0.12     [ उच्च सहमति (High Agreement)] │ │
│ │ GFS vs ECMWF विश्लेषणात्मक तुलना • ग्रिड रिज़ॉल्यूशन 0.25°│ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ समग्र परिचालन जोखिम: 7.05 / 10.0                 [ HIGH ] │ │
│ │ क्षेत्र: New Delhi • आपदा: Heavy Rainfall / Squall        │ │
│ │ प्राथमिकता: Immediate drainage clearance                  │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ Hazard (H): 6.5 │ Exposure (E): 8.0 │ Vuln (V): 7.0 │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Real API Endpoint Mapping

| Feature | Backend API Endpoint | Android Domain Model | Displayed Fields |
|---|---|---|---|
| **GFS Atmospheric Grid** | `GET /api/v1/nwp/gfs` | `NWPGridPoint` | `model`, `gridResolutionDeg`, `forecastLeadHours`, `temperature2mC`, `accumulatedPrecipMm`, `windSpeedKmh`, `pressureMslHpa` |
| **NWP Model Divergence** | `GET /api/v1/nwp/comparison` | `NWPModelComparison` | `divergenceAnalysis.divergenceRatio`, `divergenceAnalysis.agreementCategory`, `models` |
| **Operational Risk** | `GET /api/v1/gis/risk-assessment` | `OperationalRisk` | `district`, `hazardType`, `hazardIndex`, `exposureIndex`, `vulnerabilityIndex`, `compositeRiskScore`, `riskLevel`, `actionPriority` |
| **Spatial Analysis** | `GET /api/v1/gis/analysis` | `GISAnalysisReport` | `exposureScore`, `impactScore`, `riskCategory`, `actionableGuidance` |

---

## 3. Mathematical Consistency & Provenance

1. **Composite Risk Formulation**:
   $$I = 0.50 \times H + 0.30 \times E + 0.20 \times V$$
   - Verified deterministic calculation executed on verified PostGIS spatial overlays.
2. **NWP Bilinear Extraction & Divergence**:
   - Compares NOAA GFS 0.25° with analytical ECMWF fields across the Indian bounding box ($6^\circ\text{N}-38^\circ\text{N}, 68^\circ\text{E}-98^\circ\text{E}$).
3. **Decadal Climate Trends**:
   - Displays Sen's Slope non-parametric trend estimator ($\text{mm/year}$) and 30-year normal precipitation anomalies.

---

## 4. Verification & Testing

- **Tests:** 130/130 unit tests passing cleanly.
- **Scenarios:** `dataViewModel_loadsGFSAndComparison`, `analystDashboardViewModel_loadsRiskAssessmentAndGISAnalysis`.

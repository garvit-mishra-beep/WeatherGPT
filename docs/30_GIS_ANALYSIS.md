# WeatherGPT B7 — GIS Analysis Specification & Implementation

**Document:** `docs/30_GIS_ANALYSIS.md`  
**Milestone:** B7 — GIS Analysis (Canonical GIS/Backend Roadmap)  
**Repository:** `WeatherGPT`  
**Authoritative Specs:** [`docs/09_GIS_SPEC.md`](docs/09_GIS_SPEC.md), [`docs/11_ANALYTICS_ENGINE.md`](docs/11_ANALYTICS_ENGINE.md), [`docs/24_ANALYTICS_ENGINE_IMPLEMENTATION.md`](docs/24_ANALYTICS_ENGINE_IMPLEMENTATION.md), [`docs/27_SPATIAL_ENGINE.md`](docs/27_SPATIAL_ENGINE.md), [`docs/29_WEATHER_GIS_INTEGRATION.md`](docs/29_WEATHER_GIS_INTEGRATION.md)

---

## 1. Executive Overview & System Boundary

The **GIS Analysis** layer (`app/gis/analysis/`) is the deterministic mathematical and spatial analysis engine that translates raw meteorological hazards and spatial boundaries into actionable risk and impact metrics:
- **Hazard Characterization & Scoring ($H \in [0.0, 10.0]$):** Evaluates rainfall percentiles, rainfall accumulation rates, wind squalls, heat wave criteria, and official IMD warnings.
- **Spatial Exposure Quantification ($E \in [0.0, 10.0]$):** Calculates geodesic overlapping area ($\text{km}^2$) and percentage overlap over administrative boundaries.
- **Regional Vulnerability Assessment ($V \in [0.0, 10.0]$):** Evaluates urbanization density and drainage capacity factors.
- **Composite Operational Impact Calculation:** Computes $\text{Impact} = (0.50 \times H) + (0.30 \times E) + (0.20 \times V)$ per `docs/11_ANALYTICS_ENGINE.md` §4.2.
- **Multi-Hazard Compounding Analysis:** Analyzes concurrent hazards with interaction multipliers (e.g. Heavy Rain + Strong Wind).

```text
    Weather & Hazard Inputs (B6 Weather × GIS)
                      │
                      ▼
               Hazard Scoring ($H$)
      (Rainfall, Wind, Heat, IMD Warnings)
                      │
                      ▼
            Spatial Exposure ($E$)
      (PostGIS Intersection & Overlap %)
                      │
                      ▼
         Regional Vulnerability ($V$)
        (Drainage & Urbanization Index)
                      │
                      ▼
      Composite Impact ($H \times E \times V$)
       0.50*H + 0.30*E + 0.20*V -> Impact Score
                      │
                      ▼
          Structured GISAnalysisResult
                      │
                      ▼
         Future Milestone: B8 Map-Ready Data
```

### Critical Architectural Invariants
1. **Zero LLM Risk Computation:** Pure deterministic mathematical formulas in Python/NumPy and spatial queries in PostGIS. Zero LLM calculations or threshold guessing.
2. **Immutable Official Warning Severity:** Official IMD warning levels (Green, Yellow, Orange, Red) are immutable.
3. **Data Integrity & Provenance:** Full calculation formulas, source provider metadata, and timestamps are attached to all responses.

---

## 2. Mathematical Formulations & Scoring Rules

### 2.1 Hazard Index ($H \in [0.0, 10.0]$)
- **Precipitation Percentile Rule (`docs/11_ANALYTICS_ENGINE.md` §4.1):**
  - $P_{\text{hist}} < 75\text{th} \implies H = 0.0$ (None)
  - $75\text{th} \le P_{\text{hist}} < 90\text{th} \implies H = 4.0$ (Moderate Hazard)
  - $90\text{th} \le P_{\text{hist}} < 97.5\text{th} \implies H = 7.5$ (Severe Hazard)
  - $P_{\text{hist}} \ge 97.5\text{th} \implies H = 10.0$ (Extreme Hazard)
- **IMD 24h Rainfall Accumulation Standard:**
  - $< 15.6\text{ mm} \implies H = 0.0$
  - $15.6 - 64.4\text{ mm} \implies H = 2.5$
  - $64.5 - 115.5\text{ mm} \implies H = 5.0$ (Heavy)
  - $115.6 - 204.4\text{ mm} \implies H = 7.5$ (Very Heavy)
  - $> 204.4\text{ mm} \implies H = 10.0$ (Extremely Heavy)
- **Official Warning Level (Immutable):**
  - Green $\implies H = 0.0$
  - Yellow $\implies H = 4.0$
  - Orange $\implies H = 7.5$
  - Red $\implies H = 10.0$

### 2.2 Exposure Index ($E \in [0.0, 10.0]$)
$$\text{Overlap \%} = \frac{A_{\text{exposed}}}{A_{\text{total}}} \times 100$$
$$E = \min(10.0, \text{Overlap \%} / 10.0)$$

### 2.3 Vulnerability Index ($V \in [0.0, 10.0]$)
$$V = (U \times 5.0) + ((10.0 - D) \times 0.5)$$
*(where $U \in [0, 1]$ is the urbanization factor and $D \in [0, 10]$ is the drainage capacity).*

### 2.4 Composite Operational Impact ($I \in [0.0, 10.0]$)
$$\text{Impact Score} = (0.50 \times H) + (0.30 \times E) + (0.20 \times V)$$

| Composite Impact Score | Risk Category | Action Priority |
| :---: | :---: | :--- |
| $0.0 - 3.4$ | **Low Risk** | Routine operational monitoring. |
| $3.5 - 6.9$ | **Medium Risk** | Issue pre-positioning alerts; inspect urban drainage. |
| $7.0 - 10.0$ | **High / Critical Risk** | Activate disaster management protocols; mobilize resources. |

---

## 3. Verification & Quality Gates

The test suite in `tests/test_gis_analysis.py` validates all operations across 16 unit and analytical tests:

```bash
$env:TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5433/weathergpt"
pytest -q tests/
```
**Results:** **400 passed in 7.00s (100% green).**

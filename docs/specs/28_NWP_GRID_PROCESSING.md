# WeatherGPT B5 — NWP Grid Processing Specification & Implementation

**Document:** `docs/28_NWP_GRID_PROCESSING.md`  
**Milestone:** B5 — NWP Grid Processing (Canonical GIS/Backend Roadmap)  
**Repository:** `WeatherGPT`  
**Authoritative Specs:** [`docs/08_NWP_SPEC.md`](08_NWP_SPEC.md), [`docs/09_GIS_SPEC.md`](09_GIS_SPEC.md), [`docs/25_METEOROLOGICAL_DATA_ADAPTERS.md`](25_METEOROLOGICAL_DATA_ADAPTERS.md)

---

## 1. Overview & Architectural Boundaries

The **NWP Grid Processing** layer (`app/nwp/`) establishes the deterministic mathematical foundation for processing Numerical Weather Prediction grids (GFS 0.25° and ECMWF IFS) over the Indian subcontinent ($6^\circ\text{N}-38^\circ\text{N}, 68^\circ\text{E}-98^\circ\text{E}$).

```text
GFS 0.25° / ECMWF NWP Ingest
        ↓
    NWP Reader (app/nwp/reader.py)
        ↓
 Grid Validation & Longitude Normalization (0-360° -> -180-180°)
        ↓
   NWP Engine (app/nwp/engine.py)
 ┌─────────────────────────────────────────────────────────────┐
 │ 2D Bilinear Grid-to-Point Interpolation (Exact Analytical)  │
 │ Spatial Grid-to-Polygon / MultiPolygon Zonal Aggregations   │
 │ Multi-Model Relative Divergence Ratio & Agreement State     │
 │ Regional Subsetting (BBox Slicing)                          │
 └─────────────────────────────────────────────────────────────┘
        ↓
Typed NWP Contracts (Pydantic v2 & Evidence Integration)
        ↓
Future Milestone: B6 (Weather × GIS)
```

### Critical Architectural Invariants
1. **Zero LLM Dependency:** NWP calculations are strictly deterministic numerical algorithms in Python and NumPy. Zero LLM atmospheric simulation.
2. **Mathematical Exactness:** 2D bilinear interpolation follows `docs/08_NWP_SPEC.md` §4.1 with NaN handling.
3. **Multi-Model Divergence:** Quantitative relative divergence ratio $DR = \frac{\max(R_i) - \min(R_i)}{\mu + 1.0}$ and Agreement State classification.
4. **Data Isolation:** NWP processing only extracts, interpolates, and aggregates prognostic fields; it does not make agricultural or risk decisions (reserved for B7 GIS Analysis).

---

## 2. Ingested Atmospheric Variables

Adhering to `docs/08_NWP_SPEC.md` §3:

| Variable | Description | Source Unit | Target Unit | Normalization Rule |
| :--- | :--- | :---: | :---: | :--- |
| `TMP:2m` | 2-Meter Air Temperature | K | °C | $T_{^{\circ}\text{C}} = T_{\text{K}} - 273.15$ |
| `RH:2m` | 2-Meter Relative Humidity | % | % | Clamped to $[0.0, 100.0]$ |
| `APCP:surface`| Accumulated Precipitation | $\text{kg/m}^2$ | mm | Equivalent to mm ($1\text{ kg/m}^2 = 1\text{ mm}$) |
| `UGRD:10m` | 10-Meter U-Wind Vector | m/s | m/s | Horizontal zonal wind |
| `VGRD:10m` | 10-Meter V-Wind Vector | m/s | m/s | Horizontal meridional wind |
| `GUST:surface`| Surface Wind Gust | m/s | km/h | $v_{\text{km/h}} = v_{\text{m/s}} \times 3.6$ |
| `PRMSL` | Mean Sea Level Pressure | Pa | hPa | $P_{\text{hPa}} = P_{\text{Pa}} / 100$ |
| `TCDC` | Total Cloud Cover | % | % | Clamped to $[0.0, 100.0]$ |

---

## 3. Mathematical Interpolation & Formulations

### 3.1 2D Bilinear Grid-to-Point Interpolation
For target coordinate $P(x, y)$ inside bounding vertices $Q_{11}(x_1, y_1), Q_{21}(x_2, y_1), Q_{12}(x_1, y_2), Q_{22}(x_2, y_2)$:

$$f(x, y) = \frac{(x_2 - x)(y_2 - y)}{(x_2 - x_1)(y_2 - y_1)} f(Q_{11}) + \frac{(x - x_1)(y_2 - y)}{(x_2 - x_1)(y_2 - y_1)} f(Q_{21}) + \frac{(x_2 - x)(y - y_1)}{(x_2 - x_1)(y_2 - y_1)} f(Q_{12}) + \frac{(x - x_1)(y - y_1)}{(x_2 - x_1)(y_2 - y_1)} f(Q_{22})$$

- Missing/NaN corner cells raise controlled `NWPInterpolationError` rather than silently substituting zero.

### 3.2 Multi-Model Agreement & Relative Divergence Ratio
1. **Ensemble Mean:** $\mu = \frac{1}{N} \sum_{i=1}^N R_i$
2. **Absolute Spread:** $\Delta R = \max(R_i) - \min(R_i)$
3. **Relative Divergence Ratio ($DR$):**
   $$DR = \frac{\Delta R}{\mu + 1.0}$$

| Divergence Ratio ($DR$) | Agreement State | Communication Directive |
| :--- | :---: | :--- |
| $DR \le 0.25$ | **High Agreement** | High confidence: Major models are in strong physical agreement. |
| $0.25 < DR \le 0.65$ | **Moderate Agreement** | Moderate agreement: Models agree on occurrence with minor intensity variations. |
| $DR > 0.65$ | **High Disagreement** | High disagreement: Notable model divergence; monitor official IMD updates. |

---

## 4. Verification & Quality Gates

The test suite in `tests/test_nwp_grid.py` validates all NWP operations across 18 comprehensive tests:

```bash
pytest -q tests/test_nwp_grid.py
```
**Results:** 18 passed in 0.33s.

Full repository test suite:
```bash
$env:TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5433/weathergpt"
pytest -q tests/
```
**Results:** **375 passed in 6.65s (100% green).**

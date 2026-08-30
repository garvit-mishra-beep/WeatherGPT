# Deterministic Analytics Engine (`app/analytics/`)

## 1. Philosophy & Strict Non-LLM Invariant
The **Analytics Engine** is the deterministic mathematical heart of WeatherGPT.

$$\text{Data Ingest / Verification} \longrightarrow \text{Analytics Engine} \longrightarrow \text{Evidence Package} \longrightarrow \text{LLM Interpretation}$$

> [!IMPORTANT]
> **Strict Non-LLM Computation Rule**: No mathematical calculation, statistical test, trend slope, reference evapotranspiration ($ET_0$), water balance deficit, or risk score may ever be estimated, approximated, or calculated by an LLM. All numerical computations occur in verified, unit-checked, deterministic Python / NumPy algorithms.

## 2. Package Architecture
```text
app/analytics/
├── __init__.py           # Public exports (calculate_et0, run_mann_kendall, calculate_sen_slope, etc.)
├── README.md             # This document
├── types.py              # Pydantic v2 typed inputs, outputs, enums, & flags
├── errors.py             # Error taxonomy (AnalyticsError, UnitValidationError, etc.)
├── validation.py         # Physical range checks, missing data policy, finite number assertions
├── common.py             # Pure psychrometric & normal distribution mathematical functions
├── et0.py                # FAO-56 Penman-Monteith Reference Evapotranspiration engine
├── trends.py             # Mann-Kendall monotonic trend test & Sen's slope estimator
├── water_balance.py      # Crop ETc, effective precipitation, soil water deficit & irrigation advisory
└── risk.py               # Empirical percentile hazard index & composite risk score engine
```

## 3. Supported Calculation Engines

### 3.1 FAO-56 Penman-Monteith ET0 (`app/analytics/et0.py`)
Computes standardized daily grass reference evapotranspiration ($ET_0$ in $\text{mm/day}$):

$$ET_0 = \frac{0.408 \Delta (R_n - G) + \gamma \frac{900}{T + 273} u_2 (e_s - e_a)}{\Delta + \gamma (1 + 0.34 u_2)}$$

- **Units**: Temperature in °C, Wind speed in $\text{m/s}$, Solar radiation in $\text{MJ/m}^2/\text{day}$, Output in $\text{mm/day}$.
- **Intermediate Values**: Saturation vapor pressure ($e_s$), actual vapor pressure ($e_a$), vapor pressure deficit ($\text{vpd}$), slope of saturation curve ($\Delta$), psychrometric constant ($\gamma$), radiative and aerodynamic terms.

### 3.2 Mann-Kendall Monotonic Trend Test (`app/analytics/trends.py`)
Non-parametric test for multi-decadal climate time-series:
- **Test Statistic $S$**: Sum of sign of all pairwise differences $\sum \text{sgn}(x_j - x_k)$.
- **Variance with Tied Groups**: Exact formula accounting for repeated observation groups $t_p$.
- **Standardized Statistic $Z$ & Two-Tailed $p$-value**: Using normal distribution CDF.

### 3.3 Sen's Non-Parametric Slope Estimator (`app/analytics/trends.py`)
Calculates median pairwise slope:
$$\beta = \text{Median}\left(\frac{x_j - x_k}{t_j - t_k}\right)$$
Includes 95% confidence intervals based on rank statistics.

### 3.4 Crop Water Balance & Irrigation Decision Matrix (`app/analytics/water_balance.py`)
- **Crop Evapotranspiration**: $ET_c = K_c \times ET_0$.
- **FAO Effective Precipitation**: $P_{\text{eff}} = 0.8 \times P - 5.0$ if $P > 10.0\text{ mm}$, else $0.0$.
- **Net Deficit**: $D_{\text{net}} = ET_c - P_{\text{eff}}$.
- **Irrigation Advisory Decision**:
  - $D_{\text{net}} \le 0\text{ mm} \implies$ `POSTPONE` (Surplus / adequate moisture)
  - $D_{\text{net}} > 0\text{ mm} \land P_{\text{48h}} \ge 15.0\text{ mm} \implies$ `POSTPONE` (Imminent rain)
  - $D_{\text{net}} > 10.0\text{ mm} \land P_{\text{48h}} < 5.0\text{ mm} \implies$ `IRRIGATE` (Critical moisture stress)
  - Otherwise $\implies$ `MONITOR`.
- **Chemical Spray Window**: Suitable if $u_{\text{wind}} \le 15\text{ km/h} \land P_{\text{prob}} \le 30\% \land P_{\text{4h}} = 0\text{ mm}$.

### 3.5 Hazard & Composite Risk Scoring (`app/analytics/risk.py`)
- **Precipitation Percentile Hazard Index $H \in [0.0, 10.0]$**: $<75\text{th} \to 0.0$, $75\text{th}-90\text{th} \to 4.0$, $90\text{th}-97.5\text{th} \to 7.5$, $\ge 97.5\text{th} \to 10.0$.
- **Composite Operational Risk**: $0.50 \times H + 0.30 \times E + 0.20 \times V$.

## 4. Usage Example
```python
from app.analytics import calculate_et0, run_mann_kendall, calculate_crop_water_balance

# 1. Calculate ET0
et0_result = calculate_et0(
    temp_c=28.0,
    relative_humidity_pct=55.0,
    wind_speed_2m_ms=2.5,
    solar_radiation_mj_m2_day=20.0,
    elevation_m=50.0,
)
print(f"ET0: {et0_result.et0_mm_day} mm/day")

# 2. Crop Water Balance
wb = calculate_crop_water_balance(
    et0_mm_day=et0_result.et0_mm_day,
    crop_coefficient_kc=1.1,
    precipitation_mm=0.0,
    forecast_rain_48h_mm=2.0,
)
print(f"Action: {wb.advisory_action.value} - {wb.operational_guidance}")
```

## 5. Testing
```powershell
pytest tests/test_analytics.py -v
```

# Deterministic Analytics Engine (`app/analytics/`)

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![NumPy](https://img.shields.io/badge/NumPy-1.26%2B-013243.svg?style=flat-square&logo=numpy&logoColor=white)](https://numpy.org/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2.9.0-E92063.svg?style=flat-square&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![Tests](https://img.shields.io/badge/Analytics%20Tests-31%20Passing-brightgreen.svg?style=flat-square&logo=pytest&logoColor=white)](../../tests/)

**Pure Mathematical, Climatological & Agronomic Computing Engines for WeatherGPT**

</div>

---

## 1. Philosophy & Strict Non-LLM Invariant

The **Analytics Engine** is the deterministic computational heart of WeatherGPT.

$$\text{Data Ingestion} \longrightarrow \text{Analytics Engine} \longrightarrow \text{Evidence Package} \longrightarrow \text{LLM Interpretation}$$

> [!IMPORTANT]
> **Strict Non-LLM Computation Rule**: No mathematical calculation, statistical hypothesis test, trend slope, reference evapotranspiration ($ET_0$), water balance deficit, or risk score may ever be approximated or calculated by an LLM. All computations occur strictly in verified, unit-checked, deterministic Python and NumPy algorithms.

---

## 2. Package Architecture

```text
app/analytics/
├── __init__.py           # Public exports (calculate_et0, run_mann_kendall, calculate_sen_slope, etc.)
├── types.py              # Pydantic v2 typed inputs, outputs, enums, & flags
├── errors.py             # Error taxonomy (AnalyticsError, UnitValidationError, etc.)
├── validation.py         # Physical range checks, missing data policy, finite number assertions
├── common.py             # Pure psychrometric & normal distribution mathematical functions
├── et0.py                # FAO-56 Penman-Monteith Reference Evapotranspiration engine
├── trends.py             # Mann-Kendall monotonic trend test & Sen's slope estimator
├── water_balance.py      # Crop ETc, effective precipitation, soil water deficit & irrigation advisory
└── risk.py               # Empirical percentile hazard index & composite risk score engine
```

---

## 3. Mathematical Engines Catalog

### 3.1 FAO-56 Penman-Monteith Reference Evapotranspiration ($ET_0$)
Computes standardized daily grass reference evapotranspiration ($ET_0$ in $\text{mm/day}$):

$$ET_0 = \frac{0.408 \Delta (R_n - G) + \gamma \frac{900}{T + 273} u_2 (e_s - e_a)}{\Delta + \gamma (1 + 0.34 u_2)}$$

- **Inputs**: Temperature ($T$ in °C), Wind speed ($u_2$ in $\text{m/s}$ at 2m height), Solar radiation ($R_n$ in $\text{MJ/m}^2/\text{day}$), Soil heat flux ($G$), Relative humidity ($\text{RH}$ in %).
- **Intermediate Outputs**: Saturation vapor pressure ($e_s$), actual vapor pressure ($e_a$), vapor pressure deficit ($\text{VPD}$), slope of saturation vapor pressure curve ($\Delta$), and psychrometric constant ($\gamma$).

### 3.2 Mann-Kendall Monotonic Trend Test
Non-parametric rank-based statistical hypothesis test for multi-decadal climate time-series:
- **Test Statistic $S$**:
  $$S = \sum_{k=1}^{n-1} \sum_{j=k+1}^n \text{sgn}(x_j - x_k)$$
- **Exact Variance with Tied Groups**:
  $$\text{Var}(S) = \frac{n(n-1)(2n+5) - \sum_{i=1}^m t_i(t_i-1)(2t_i+5)}{18}$$
- **Standardized Test Statistic $Z$ & Two-Tailed $p$-value**:
  $$Z = \begin{cases} \frac{S-1}{\sqrt{\text{Var}(S)}} & \text{if } S > 0 \\ 0 & \text{if } S = 0 \\ \frac{S+1}{\sqrt{\text{Var}(S)}} & \text{if } S < 0 \end{cases}$$

### 3.3 Sen's Non-Parametric Slope Estimator
Calculates the median rate of climatological change:
$$\beta = \text{median}\left\{ \frac{x_j - x_k}{j - k} : j > k \right\}$$
Includes exact 95% confidence intervals based on the standard normal rank distribution.

### 3.4 Crop Water Balance & Irrigation Decision Matrix
- **Crop Evapotranspiration**: $ET_c = (K_{cb} + K_e) \times ET_0$.
- **FAO Effective Precipitation**:
  $$P_{\text{eff}} = \begin{cases} 0.8 \times P - 5.0 & \text{if } P > 10.0\text{ mm} \\ 0.0 & \text{if } P \le 10.0\text{ mm} \end{cases}$$
- **Net Soil Moisture Deficit**: $D_{\text{net}} = ET_c - P_{\text{eff}}$.
- **Irrigation Action Matrix**:
  - $D_{\text{net}} \le 0\text{ mm} \implies$ `POSTPONE` (Moisture surplus).
  - $D_{\text{net}} > 0\text{ mm} \land P_{\text{48h}} \ge 15.0\text{ mm} \implies$ `POSTPONE` (Rain forecasted within 48 hours).
  - $D_{\text{net}} > 10.0\text{ mm} \land P_{\text{48h}} < 5.0\text{ mm} \implies$ `IRRIGATE` (Critical root-zone stress).
  - Otherwise $\implies$ `SUITABLE` / `MONITOR`.

### 3.5 Chemical Spray Suitability Window
Determines pesticide/fertilizer application safety:
- **Wind Speed**: $u_{\text{wind}} \le 15\text{ km/h}$ (Prevents airborne drift).
- **Precipitation Probability**: $P_{\text{prob}} \le 30\%$ and 6-hour rain forecast $= 0.0\text{ mm}$ (Prevents chemical wash-off).
- **Temperature Threshold**: $T_{\text{max}} \le 35^\circ\text{C}$ (Prevents chemical evaporation/scorch).

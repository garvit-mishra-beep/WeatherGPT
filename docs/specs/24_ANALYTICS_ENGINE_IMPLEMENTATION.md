# WeatherGPT — Deterministic Analytics Engine Implementation Specification (B4)

**Document:** `24_ANALYTICS_ENGINE_IMPLEMENTATION.md`  
**Status:** Approved Technical Specification (B4 — Deterministic Analytics Engines)  
**Primary Product Authority:** [docs/01_PRD.md](01_PRD.md)  
**Related Specs:** [03_LLM_BRAIN_SPEC.md](03_LLM_BRAIN_SPEC.md), [05_TOOL_REGISTRY.md](05_TOOL_REGISTRY.md), [11_ANALYTICS_ENGINE.md](11_ANALYTICS_ENGINE.md), [20_PERFORMANCE.md](20_PERFORMANCE.md)

---

## 1. Executive Summary & Non-LLM Invariant

The **Deterministic Analytics Engine** (`app/analytics/`) executes all mathematical, physical, and statistical computations for WeatherGPT.

> [!IMPORTANT]
> **Strict Non-LLM Invariant:** The LLM is strictly an NLP reasoning, semantic routing, and explanation layer. All calculations for reference evapotranspiration ($ET_0$), Mann-Kendall statistics, Sen's slope, crop water balance, and composite risk scoring execute in pure Python / NumPy engines.

---

## 2. Mathematical Equations & Physical Formulations

### 2.1 FAO-56 Penman-Monteith Reference Evapotranspiration ($ET_0$)
Standardized daily grass reference evapotranspiration ($ET_0$ in $\text{mm/day}$):

$$ET_0 = \frac{0.408 \Delta (R_n - G) + \gamma \frac{900}{T + 273} u_2 (e_s - e_a)}{\Delta + \gamma (1 + 0.34 u_2)}$$

1. **Saturation Vapour Pressure ($e_s$ in $\text{kPa}$):**
   $$e^\circ(T) = 0.6108 \exp\left(\frac{17.27 T}{T + 237.3}\right)$$
   $$e_s = \frac{e^\circ(T_{\max}) + e^\circ(T_{\min})}{2} \quad (\text{or } e^\circ(T_{\text{mean}}))$$
2. **Actual Vapour Pressure ($e_a$ in $\text{kPa}$):**
   $$e_a = \frac{RH}{100} e_s$$
3. **Slope of Saturation Vapour Pressure Curve ($\Delta$ in $\text{kPa/}^\circ\text{C}$):**
   $$\Delta = \frac{4098 \cdot e^\circ(T)}{(T + 237.3)^2}$$
4. **Psychrometric Constant ($\gamma$ in $\text{kPa/}^\circ\text{C}$):**
   $$\gamma = 0.000665 \times P$$
   where atmospheric pressure $P = 101.3 \left(\frac{293 - 0.0065 z}{293}\right)^{5.26}$ for elevation $z$ in meters.

---

### 2.2 Mann-Kendall Monotonic Trend Test
Detects non-parametric trends in historical climate series ($n \ge 3$):

1. **$S$ Statistic:**
   $$S = \sum_{k=1}^{n-1} \sum_{j=k+1}^n \text{sgn}(x_j - x_k)$$
2. **Tied-Group Variance $\text{Var}(S)$:**
   $$\text{Var}(S) = \frac{1}{18} \left[ n(n-1)(2n+5) - \sum_{p=1}^g t_p(t_p-1)(2t_p+5) \right]$$
3. **Standardized $Z$ Score & Asymptotic Two-Tailed $p$-value:**
   $$Z = \begin{cases} \frac{S-1}{\sqrt{\text{Var}(S)}} & S > 0 \\ 0 & S = 0 \\ \frac{S+1}{\sqrt{\text{Var}(S)}} & S < 0 \end{cases}, \quad p = \text{erfc}\left(\frac{|Z|}{\sqrt{2}}\right)$$

---

### 2.3 Sen's Robust Non-Parametric Slope Estimator
Quantifies trend rate $\beta$ ($\Delta\text{unit} / \text{time step}$):

$$\beta = \text{Median}\left(\frac{x_j - x_k}{t_j - t_k}\right) \quad \forall \ 1 \le k < j \le n$$

Includes $95\%$ confidence interval $[Q_{\text{lower}}, Q_{\text{upper}}]$ derived from normal rank order statistics.

---

### 2.4 Agronomic Water Balance & Irrigation Decision Matrix
1. **Crop Evapotranspiration:** $ET_c = K_c \times ET_0$.
2. **FAO Effective Precipitation:**
   $$P_{\text{eff}} = \begin{cases} 0.8 \times P - 5.0 & P > 10.0\text{ mm} \\ 0.0 & P \le 10.0\text{ mm} \end{cases}$$
3. **Net Water Balance Deficit:** $D_{\text{net}} = ET_c - P_{\text{eff}}$.
4. **Irrigation Advisory Matrix:**
   * $D_{\text{net}} \le 0\text{ mm} \implies$ `POSTPONE` (Surplus / adequate moisture)
   * $D_{\text{net}} > 0\text{ mm} \land P_{\text{48h}} \ge 15.0\text{ mm} \implies$ `POSTPONE` (Rain expected; avoid waterlogging)
   * $D_{\text{net}} > 10.0\text{ mm} \land P_{\text{48h}} < 5.0\text{ mm} \implies$ `IRRIGATE` (Crop moisture stress)
   * Otherwise $\implies$ `MONITOR`.
5. **Chemical Spray Window Suitability:**
   $$\text{Suitable} = (u_{\text{wind}} \le 15\text{ km/h}) \land (P_{\text{prob}} \le 30\%) \land (P_{\text{4h post-spray}} = 0\text{ mm})$$

---

### 2.5 Multi-Criteria Operational Risk Engine
1. **Precipitation Percentile Hazard Index $H \in [0.0, 10.0]$:**
   * $P_{\text{hist}} < 75\text{th} \to 0.0$
   * $75\text{th} \le P_{\text{hist}} < 90\text{th} \to 4.0$ (Moderate Hazard)
   * $90\text{th} \le P_{\text{hist}} < 97.5\text{th} \to 7.5$ (Severe Hazard)
   * $P_{\text{hist}} \ge 97.5\text{th} \to 10.0$ (Extreme Hazard)
2. **Composite Risk Score:**
   $$\text{Risk Score} = 0.50 \times H + 0.30 \times E + 0.20 \times V$$
   * $0.0 - 3.4 \implies$ Low Risk (Routine monitoring)
   * $3.5 - 6.9 \implies$ Medium Risk (Pre-positioning alerts)
   * $7.0 - 10.0 \implies$ High / Critical Risk (Disaster protocol activation)

---

## 3. Module Layout (`app/analytics/`)

```text
app/analytics/
├── __init__.py           # Unified entry point for all calculation engines
├── types.py              # Pydantic v2 typed inputs, outputs, & intermediate records
├── errors.py             # AnalyticsError taxonomy
├── validation.py         # Physical bounds, missing data check, finite assertions
├── common.py             # Pure math, psychrometric & normal distribution helpers
├── et0.py                # FAO-56 Penman-Monteith ET0 engine
├── trends.py             # Mann-Kendall trend test & Sen's slope estimator
├── water_balance.py      # Crop ETc, effective rainfall, soil deficit & spray safety
├── risk.py               # Empirical percentile hazard index & composite risk
└── README.md             # Package documentation
```

---

## 4. Verification & Testing

Validated across 31 dedicated unit tests in `tests/test_analytics.py`:
- FAO-56 benchmark verification with split $T_{\max}/T_{\min}$, zero wind, and high radiation.
- Mann-Kendall with increasing, decreasing, constant, and tied groups.
- Sen's slope with regular and irregular time intervals.
- Invariant tests: time reversal flips trend sign and slope; repeated runs are byte-identical.

# WeatherGPT — Deterministic Analytics Engine Specification

**Document:** `11_ANALYTICS_ENGINE.md`  
**Status:** Approved Technical Specification  
**Primary PRD Reference:** [docs/01_PRD.md](01_PRD.md)  
**Related Specs:** [03_LLM_BRAIN_SPEC.md](03_LLM_BRAIN_SPEC.md), [05_TOOL_REGISTRY.md](05_TOOL_REGISTRY.md), [08_NWP_SPEC.md](08_NWP_SPEC.md)

---

## 1. Analytics Engine Philosophy & Core Tenet

The Analytics Engine is the deterministic mathematical heart of WeatherGPT.

$$\text{Pure Mathematical Functions in Python / SciPy / NumPy} \longrightarrow \text{Exact Numbers & Provenance} \longrightarrow \text{LLM Interpretation}$$

> [!IMPORTANT]
> **Strict Non-LLM Computation Rule:** No statistical test, trend slope, reference evapotranspiration ($ET_0$), water balance deficit, or risk index may ever be calculated, guessed, or approximated by the LLM. The LLM receives the verified output of the Analytics Engine in the Evidence Package and provides context-rich explanations.

---

## 2. Research & Climate Statistical Analytics

### 2.1 Mann-Kendall Monotonic Trend Test
Used to detect statistically significant non-parametric monotonic trends in multi-decadal historical climate series.

1. **Test Statistic $S$:**
   $$S = \sum_{k=1}^{n-1} \sum_{j=k+1}^{n} \text{sgn}(x_j - x_k)$$
   $$\text{sgn}(\theta) = \begin{cases} +1 & \text{if } \theta > 0 \\ 0 & \text{if } \theta = 0 \\ -1 & \text{if } \theta < 0 \end{cases}$$

2. **Variance with Tie Correction:**
   $$\text{Var}(S) = \frac{1}{18} \left[ n(n-1)(2n+5) - \sum_{p=1}^{g} t_p(t_p-1)(2t_p+5) \right]$$
   *(where $g$ is the number of tied groups and $t_p$ is the number of data points in the $p$-th group).*

3. **Standardized Test Statistic $Z$:**
   $$Z = \begin{cases} \frac{S-1}{\sqrt{\text{Var}(S)}} & \text{if } S > 0 \\ 0 & \text{if } S = 0 \\ \frac{S+1}{\sqrt{\text{Var}(S)}} & \text{if } S < 0 \end{cases}$$
   *Decision:* If $p$-value $< 0.05$ (two-tailed $\alpha = 0.05$, $|Z| > 1.96$), the trend is marked **statistically significant**.

### 2.2 Sen's Non-Parametric Slope Estimator
Computes the true robust magnitude of trend change ($\Delta\text{ unit}/\text{year}$):
$$\beta = \text{Median} \left( \frac{x_j - x_k}{j - k} \right) \quad \forall \ 1 \le k < j \le n$$

---

## 3. Farmer Agronomic Intelligence & Evapotranspiration

### 3.1 FAO-56 Penman-Monteith Reference Evapotranspiration ($ET_0$)
Computes standardized grass reference evapotranspiration ($ET_0$ in $\text{mm/day}$):

$$ET_0 = \frac{0.408 \Delta (R_n - G) + \gamma \frac{900}{T + 273} u_2 (e_s - e_a)}{\Delta + \gamma (1 + 0.34 u_2)}$$

* **Parameters:**
  * $R_n$: Net solar radiation at the crop surface ($\text{MJ/m}^2/\text{day}$).
  * $G$: Soil heat flux density ($\text{MJ/m}^2/\text{day}$, taken as $0$ for daily calculations).
  * $T$: Mean daily air temperature at $2\text{ m}$ height (°C).
  * $u_2$: Wind speed at $2\text{ m}$ height ($\text{m/s}$).
  * $e_s$: Saturation vapour pressure ($\text{kPa}$).
  * $e_a$: Actual vapour pressure ($\text{kPa}$).
  * $\Delta$: Slope of saturation vapour pressure curve ($\text{kPa/}^\circ\text{C}$).
  * $\gamma$: Psychrometric constant ($\approx 0.066\text{ kPa/}^\circ\text{C}$).

### 3.2 Crop Water Requirement ($ET_c$) & Daily Water Balance Deficit
1. **Crop Evapotranspiration:**
   $$ET_c = K_c \times ET_0$$
   *(where $K_c$ is the dynamic stage-specific crop coefficient from `crop_stages`).*

2. **Effective Precipitation ($P_{\text{eff}}$):**
   $$P_{\text{eff}} = \begin{cases} 0.8 \times P - 5.0 & \text{if } P > 10.0\text{ mm} \\ 0.0 & \text{if } P \le 10.0\text{ mm} \end{cases}$$

3. **Net Water Balance Deficit ($D_{\text{net}}$):**
   $$D_{\text{net}} = ET_c - P_{\text{eff}}$$

### 3.3 Irrigation Decision Matrix
| Net Deficit Condition ($D_{\text{net}}$) | Forecast Rain (Next 48h) | Advisory Action | Operational Guidance |
| :--- | :--- | :---: | :--- |
| $D_{\text{net}} \le 0\text{ mm}$ (Surplus) | Any | **POSTPONE** | Soil moisture adequate/surplus; postpone irrigation. |
| $D_{\text{net}} > 0\text{ mm}$ (Deficit) | $P_{\text{48h}} \ge 15.0\text{ mm}$ | **POSTPONE** | Rain expected; withhold irrigation to avoid waterlogging. |
| $D_{\text{net}} > 10.0\text{ mm}$ (Critical) | $P_{\text{48h}} < 5.0\text{ mm}$ | **IRRIGATE** | Crop moisture stress detected; schedule irrigation immediately. |

### 3.4 Chemical Spray Suitability Logic
Evaluates whether atmospheric conditions are within agronomically safe spray windows:

$$\text{Spray Suitability} = \begin{cases} 
\text{TRUE (Suitable)} & \text{if } u_{\text{wind}} \le 15\text{ km/h} \ \land \ P_{\text{prob}} \le 30\% \ \land \ P_{\text{4h post-spray}} = 0\text{ mm} \\
\text{FALSE (Unsuitable)} & \text{otherwise}
\end{cases}$$

---

## 4. Analyst Risk Quantification Engine

### 4.1 Hazard Index ($H \in [0.0, 10.0]$)
Deterministic scoring based on the historical empirical percentile ($P_{\text{hist}}$) of the forecast 24h precipitation:

$$H = \begin{cases} 
0.0 & \text{if } P_{\text{hist}} < 75\text{th percentile} \\
4.0 & \text{if } 75\text{th} \le P_{\text{hist}} < 90\text{th percentile} \quad (\text{Moderate Hazard}) \\
7.5 & \text{if } 90\text{th} \le P_{\text{hist}} < 97.5\text{th percentile} \quad (\text{Severe Hazard}) \\
10.0 & \text{if } P_{\text{hist}} \ge 97.5\text{th percentile} \quad (\text{Extreme Hazard})
\end{cases}$$

### 4.2 Composite Operational Risk Score
$$\text{Risk Score} = (0.50 \times H) + (0.30 \times E) + (0.20 \times V)$$

* $H$: Hazard Index ($0–10$).
* $E$: Exposure Index ($0–10$, derived from PostGIS intersection with population/infrastructure density).
* $V$: Vulnerability Index ($0–10$, based on regional drainage and housing typology).

| Composite Risk Score | Risk Category | Action Priority |
| :---: | :---: | :--- |
| $0.0 - 3.4$ | **Low Risk** | Routine operational monitoring. |
| $3.5 - 6.9$ | **Medium Risk** | Issue pre-positioning alerts; inspect urban drainage. |
| $7.0 - 10.0$ | **High / Critical Risk**| Activate disaster management protocols; mobilize resources. |

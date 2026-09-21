# Vayubodhak Deterministic Climate Intelligence Engine

**Document:** `docs/CLIMATE_INTELLIGENCE_IMPLEMENTATION.md`  
**System Layer:** Climate Intelligence, Climatological Normals, and Statistical Analytics  
**Primary Mandate:** Deterministic weather departures, WMO standardized anomalies, precipitation spells, and non-parametric monotonic trend evaluation with Gemma 4:e2b natural-language explanation.

---

## 1. Executive Summary & Core Architectural Invariants

The **Climate Intelligence Engine** equips Vayubodhak with historical and climatological reasoning to answer questions such as:
* *"Is this month hotter than normal in Delhi?"*
* *"Has rainfall been below normal recently?"*
* *"Is this location experiencing a dry spell?"*
* *"Has monsoon rainfall been increasing or decreasing over recent years?"*
* *"Is this heat event anomalous or normal seasonal variation?"*

### Immutable Architectural Principles
1. **Deterministic Authority**: The LLM (Gemma 4:e2b) **never calculates** statistics, departures, percentiles, or trends. All calculations run strictly in verified NumPy/Python mathematical algorithms.
2. **Zero Climatological Fabrication**: The system **never invents** historical normals, averages, or baseline values. When an official baseline is unavailable for a given station or month, the engine explicitly reports `baseline_available = False` and clarifies that anomalies cannot be determined.
3. **Model Honesty & Provenance**: If multi-model reanalysis or WRF comparison is unavailable, the engine explicitly says so. It never claims multi-model consensus unless evidence contains verified model agreement.
4. **Explanation-Only LLM Boundary**: Gemma 4:e2b (hosted on remote laptop `UJJWAL:11434`) strictly translates pre-computed, verified evidence packages into natural language.
5. **Fail-Safe Fallbacks**: If Gemma is offline, times out, or hallucinates a contradiction, the backend gracefully falls back to deterministic natural-language summaries without raising HTTP 500 errors.

---

## 2. System Architecture

```text
User Query / API Request
        │
        ▼
[POST /api/v1/climate/analyze] ──or── [ResearcherBrain Tool Gateway]
        │
        ▼
[ClimateIntelligenceService]
   ├── 1. Data Ingestion & Quality Audit (evaluate_data_quality)
   │        • Physical sanity boundary checks (-50°C to +60°C; rain >= 0 mm)
   │        • Observation coverage percentage (>=85% VALID; 60-85% PARTIAL; <60% INSUFFICIENT)
   │
   ├── 2. Baseline Resolver (ClimateNormalsEngine)
   │        • User-supplied custom baseline (if explicitly provided)
   │        • Official WMO 1991–2020 IMD Observatory Climatology
   │        • Fallback: baseline_available = False (Zero guessing)
   │
   └── 3. Deterministic Analytics Engine
            • Temperature Metrics: Mean, Min, Max, IMD Official Heatwave Criteria
            • Precipitation Metrics: Cumulative, Daily Mean, Rainy Days (>=1.0 mm & >=2.5 mm)
            • Consecutive Spell Counters: CDD (Dry Days), CWD (Wet Days), Rx1day, Rx5day, R10mm, R20mm
            • WMO Anomaly Engine: Absolute Departure, Departure %, Standardized Z-Score (Z >= 2.0σ Extreme)
            • Monotonic Trend Engine: Mann-Kendall monotonic test & Sen's robust slope estimator
        │
        ▼
[ClimateEvidence] (Verified Immutable Data Container)
        │
        ├── [include_explanation = False] ──► Return Raw Deterministic Response
        │
        └── [include_explanation = True]
                  │
                  ▼
        [ClimateExplanationBridge]
                  │
                  ▼
        Gemma 4:e2b (via Ollama on http://UJJWAL:11434)
                  │
                  ▼
        Contradiction Guard
            ├── Clean / Aligned ──► Return Natural-Language Explanation
            └── Contradiction / Timeout ──► Safe Deterministic Fallback Explanation
```

---

## 3. Data Sources & Verified Baselines

### 3.1 Official Climatological Normals (WMO 1991–2020)
* **Authoritative Source**: *India Meteorological Department (IMD) Climatological Tables of Observatories in India (1991–2020)*.
* **Coverage**: Verified monthly empirical distributions for major meteorological hubs (Delhi/Safdarjung, Mumbai/Santacruz, Gwalior Airport, Kolkata/Alipore, etc.).
* **Stored Parameters**:
  * $\mu_{\text{temp}}$: Normal mean monthly temperature (°C)
  * $\sigma_{\text{temp}}$: Standard deviation of monthly temperature (°C)
  * $T_{\text{max},\text{normal}}$: Normal maximum temperature (°C)
  * $T_{\text{min},\text{normal}}$: Normal minimum temperature (°C)
  * $R_{\text{normal}}$: Normal monthly cumulative precipitation (mm)
  * $R_{p90}$: 90th percentile wet threshold (mm)

### 3.2 Unverified Locations / Missing Records Policy
If an inquiry targets a location, tehsil, or period for which no verified official baseline exists:
$$\text{baseline\_available} = \text{False}$$
$$\text{anomaly} = \text{None}$$
$$\text{category} = \text{Unavailable}$$
$$\text{uncertainty} = [\text{"Historical climatological baseline unavailable for this location/month. Anomaly cannot be computed."}]$$

---

## 4. Mathematical Methodology

### 4.1 Climatological Anomaly & Departure
For observed value $X_{\text{obs}}$ and baseline normal $\mu_{\text{base}}$:
$$\text{Absolute Anomaly} = X_{\text{obs}} - \mu_{\text{base}}$$

Where baseline normal $\mu_{\text{base}} \neq 0$:
$$\text{Anomaly Percentage} = \frac{X_{\text{obs}} - \mu_{\text{base}}}{|\mu_{\text{base}}|} \times 100\%$$
*(If $\mu_{\text{base}} = 0$, percentage anomaly safely returns `None` to prevent division by zero).*

Standardized departure ($Z$-score):
$$Z = \frac{X_{\text{obs}} - \mu_{\text{base}}}{\sigma_{\text{base}}}$$

#### WMO Standard Classification Matrix:
* $Z \ge +2.0$: **Severely Above Normal** (Extreme Anomaly)
* $+1.0 \le Z < +2.0$: **Above Normal**
* $-1.0 < Z < +1.0$: **Near Normal**
* $-2.0 < Z \le -1.0$: **Below Normal**
* $Z \le -2.0$: **Severely Below Normal** (Extreme Anomaly)

### 4.2 Official IMD Heatwave Classification Criteria
1. **Plains Region** (Base threshold $T_{\text{max}} \ge 40.0^\circ\text{C}$):
   * Heatwave: Departure from normal $\ge +4.5^\circ\text{C}$ OR absolute $T_{\text{max}} \ge 45.0^\circ\text{C}$.
   * Severe Heatwave: Departure from normal $\ge +6.5^\circ\text{C}$ OR absolute $T_{\text{max}} \ge 47.0^\circ\text{C}$.
2. **Hills Region** (Base threshold $T_{\text{max}} \ge 30.0^\circ\text{C}$):
   * Heatwave: Departure from normal $\ge +4.5^\circ\text{C}$.
   * Severe Heatwave: Departure from normal $\ge +6.5^\circ\text{C}$.
3. **Coastal Region** (Base threshold $T_{\text{max}} \ge 37.0^\circ\text{C}$):
   * Heatwave: Departure from normal $\ge +4.5^\circ\text{C}$.
   * Severe Heatwave: Departure from normal $\ge +6.5^\circ\text{C}$.

### 4.3 Precipitation & Spell Metrics (WMO ETCCDI)
* **CDD (Consecutive Dry Days)**: Maximum consecutive run of days with daily rainfall $< 1.0\text{ mm}$.
* **CWD (Consecutive Wet Days)**: Maximum consecutive run of days with daily rainfall $\ge 1.0\text{ mm}$.
* **Rainy Day**: Days with precipitation $\ge 1.0\text{ mm}$ (WMO standard) and $\ge 2.5\text{ mm}$ (IMD official standard).
* **Extremes**:
  * $R10\text{mm}$: Count of days where rainfall $\ge 10.0\text{ mm}$.
  * $R20\text{mm}$: Count of days where rainfall $\ge 20.0\text{ mm}$.
  * $Rx1\text{day}$: Maximum 1-day precipitation volume ($\text{mm}$).
  * $Rx5\text{day}$: Maximum 5-day rolling cumulative precipitation ($\text{mm}$).

### 4.4 Non-Parametric Monotonic Trend Analysis
* **Mann-Kendall Test Statistic $S$**:
  $$S = \sum_{k=1}^{n-1} \sum_{j=k+1}^n \text{sgn}(x_j - x_k)$$
* **Variance $\text{Var}(S)$ with tied groups correction**:
  $$\text{Var}(S) = \frac{n(n-1)(2n+5) - \sum_{p} t_p(t_p-1)(2t_p+5)}{18}$$
* **Sen's Slope Estimator**:
  $$\beta = \text{median}\left(\frac{x_j - x_i}{j - i}\right), \quad \forall j > i$$
* Evaluated at $\alpha = 0.05$ (95% confidence). Returns `INCREASING`, `DECREASING`, `STABLE`, or `INSUFFICIENT_DATA` ($n < 3$).

---

## 5. REST API Contract

### Endpoint: `POST /api/v1/climate/analyze`

#### Request Payload:
```json
{
  "location": "Delhi",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "variable": "temperature",
  "period_start": "2024-05-01",
  "period_end": "2024-05-07",
  "observations": [35.0, 36.5, 37.0, 36.0, 35.5, 36.0, 37.0],
  "region_type": "Plains",
  "include_explanation": true
}
```

#### Response Payload:
```json
{
  "evidence": {
    "location": "Delhi",
    "variable": "temperature",
    "period_start": "2024-05-01",
    "period_end": "2024-05-07",
    "sample_size": 7,
    "mean": 36.14,
    "min": 35.0,
    "max": 37.0,
    "baseline_available": true,
    "baseline_value": 33.8,
    "anomaly": 2.34,
    "anomaly_percent": 6.92,
    "anomaly_category": "Above Normal",
    "temperature_metrics": {
      "mean_c": 36.14,
      "min_c": 35.0,
      "max_c": 37.0,
      "is_heatwave": false,
      "heatwave_criteria": "Normal seasonal conditions (Heatwave criteria not triggered)"
    },
    "trend": {
      "direction": "STABLE",
      "slope": 0.1667,
      "p_value": 0.4526,
      "is_significant": false
    },
    "coverage_pct": 100.0,
    "quality": "VALID",
    "source": "IMD Climatological Tables of Observatories in India (1991-2020)",
    "units": "°C"
  },
  "explanation": "Over the first week of May 2024, Delhi recorded an average temperature of 36.1°C, which is 2.3°C above the 1991–2020 climatological normal of 33.8°C (+6.9%). Conditions are classified as Above Normal, though official heatwave thresholds were not crossed.",
  "explanation_source": "gemma4:e2b",
  "generated_at_iso": "2026-09-08T07:00:00Z"
}
```

---

## 6. Gemma 4:e2b Boundary & Safety

### Contradiction Guard
The explanation bridge monitors candidate text from Gemma:
1. **Opposite Trend / Anomaly Rejection**: If anomaly is $+2.5^\circ\text{C}$ (*Above Normal*), any statement claiming "cooler than normal" or "below normal" is caught and rejected.
2. **Fabricated Baseline Guard**: If `baseline_available = False`, any statement asserting a specific historical average is caught and rejected.
3. **Fallback Synthesis**: Whenever a contradiction or provider error occurs, `generate_deterministic_fallback_explanation` executes immediately.

---

## 7. Verification & Test Matrix

| Test Suite | File | Tests | Result |
| :--- | :--- | :---: | :--- |
| **Climate Intelligence** | `tests/test_climate_intelligence.py` | 22/22 | **PASSED (100%)** |
| **USP Phase 1, 2, 3** | `tests/test_usp_phase1_decisions.py`, `phase2`, `phase3` | 28/28 | **PASSED (100%)** |
| **USP Phase 4A Bridge** | `tests/test_usp_phase4a_explanation_bridge.py` | 11/11 | **PASSED (100%)** |
| **Ollama Remote LLM** | `tests/test_ollama_provider.py` | 19/19 | **PASSED (100%)** |
| **Android Unit Suite** | `android/app/src/test/` | 167/167 | **PASSED (100%)** |

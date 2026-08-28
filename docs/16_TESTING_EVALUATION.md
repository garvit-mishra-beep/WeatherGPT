# WeatherGPT — Testing, Validation & Evaluation Specification

**Document:** `16_TESTING_EVALUATION.md`  
**Status:** Approved Technical Specification  
**Primary PRD Reference:** [docs/01_PRD.md](01_PRD.md)  
**Related Specs:** [03_LLM_BRAIN_SPEC.md](03_LLM_BRAIN_SPEC.md), [06_API_CONTRACT.md](06_API_CONTRACT.md), [11_ANALYTICS_ENGINE.md](11_ANALYTICS_ENGINE.md), [15_ERROR_GUARDRAILS.md](15_ERROR_GUARDRAILS.md)

---

## 1. Testing Strategy & Quality Assurance Framework

WeatherGPT employs a multi-tiered testing framework combining deterministic unit testing, end-to-end integration tests, and automated LLM grounding evaluation benchmarks.

```text
┌────────────────────────────────────────────────────────────────────────────┐
│                        WEATHERGPT TESTING PYRAMID                          │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│                       / \     LLM Grounding & Hallucination Evals          │
│                      /   \    (RAG Triad, Fidelity Benchmark)              │
│                     /-----\                                                │
│                    /       \    Auto Router Intent & Multilingual Evals    │
│                   /         \   (250+ Gold Test Prompts)                   │
│                  /-----------\                                             │
│                 /             \   FastAPI End-to-End & PostGIS Tests       │
│                /               \  (pytest, TestClient, GeoJSON validation) │
│               /-----------------\                                          │
│              /                   \  Deterministic Math & Tool Unit Tests   │
│             /_____________________\ (NumPy, SciPy, FAO-56 ET0, Schemas)    │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Evaluation Metrics & Quality Targets

| Quality Dimension | Metric Definition | MVP Acceptance Target | Validation Method |
| :--- | :--- | :---: | :--- |
| **Numerical Grounding** | % of output weather numbers matching Evidence Package | **100.0%** (Zero Tolerance)| Automated Regex & AST Numerical Validator |
| **Warning Fidelity** | % of active IMD warnings preserved verbatim without downgrade | **100.0%** (Zero Tolerance)| Automated Safety Test Suite |
| **Auto Routing Accuracy**| Correct Brain dispatch rate on 250+ benchmark queries | $\ge \mathbf{95.0\%}$ | Golden Dataset Evaluation Matrix |
| **Statistical Accuracy** | Verification of Mann-Kendall $\tau$ and Sen's slope against R/SciPy | $\mathbf{100.0\%}$ ($< 10^{-6}$ error)| Analytical Unit Tests |
| **$ET_0$ Calculation Error**| Difference from FAO-56 reference standard tables | $< \mathbf{0.01\text{ mm/day}}$ | FAO Irrigation Paper 56 Benchmarks |
| **Multilingual Invariance**| % of numerical values altered during translation | $\mathbf{0.0\%}$ (Zero Mutation)| Cross-Language Numerical AST Diff |
| **API Latency (Cached)** | P95 Response time for cached weather queries | $< \mathbf{250\text{ ms}}$ | Locust Load Test ($50\text{ RPS}$) |
| **API Latency (Full LLM)**| P95 Response time for multi-tool LLM reasoning turn | $< \mathbf{4.5\text{ seconds}}$ | End-to-End Pipeline Profiling |

---

## 3. Core Test Suites Specification

### 3.1 Suite 1: Deterministic Analytics & Math Engine Tests
Validates pure mathematical algorithms without network or LLM dependencies.

```python
# test_analytics_engine.py
import pytest
import numpy as np
from app.analytics.fao56 import calculate_reference_et0
from app.analytics.stats import mann_kendall_trend, sens_slope

def test_fao56_penman_monteith_standard():
    """Validates ET0 against FAO Irrigation and Drainage Paper 56 Example 18."""
    et0 = calculate_reference_et0(
        temp_mean_c=28.5,
        temp_max_c=34.0,
        temp_min_c=23.0,
        relative_humidity_pct=65.0,
        wind_speed_2m_ms=2.1,
        solar_radiation_mj_m2=22.4,
        elevation_m=53.0,
        latitude=23.02
    )
    assert np.isclose(et0, 5.48, atol=0.05), f"Expected ET0 around 5.48 mm/day, got {et0}"

def test_mann_kendall_monotonic_trend():
    """Validates Mann-Kendall trend detection on synthetic decreasing series."""
    series = [100.0, 95.0, 92.0, 88.0, 84.0, 80.0, 75.0, 71.0, 68.0, 60.0]
    result = mann_kendall_trend(series)
    assert result.trend_direction == "decreasing"
    assert result.is_statistically_significant is True
    assert result.p_value < 0.01
```

---

### 3.2 Suite 2: Auto Router Intent & Brain Dispatch Tests
Executes 250+ canonical user queries in English, Hindi, Gujarati, Marathi, and Bengali to verify routing precision.

```python
# test_auto_router.py
import pytest
from app.router.engine import auto_route_query

ROUTER_BENCHMARKS = [
    # General Brain Queries
    ("What's the weather today in Delhi?", "general"),
    ("Will it rain tomorrow in Kolkata?", "general"),
    ("आज मुंबई में बारिश होगी क्या?", "general"),
    
    # Farmer Brain Queries
    ("Should I irrigate my wheat crop tomorrow in Karnal?", "farmer"),
    ("Can I spray pesticide on cotton tomorrow?", "farmer"),
    ("કપાસમાં ક્યારે પિયત આપવું?", "farmer"),
    ("सोयाबीन पिकावर औषध फवारणी करावी का?", "farmer"),
    
    # Researcher Brain Queries
    ("Compare monsoon rainfall in Pune over the last 30 years.", "researcher"),
    ("Show rainfall anomaly trends for Saurashtra.", "researcher"),
    
    # Analyst Brain Queries
    ("Which districts are under Red Alert and most exposed?", "analyst"),
    ("Show infrastructure exposed to heavy rain in South Gujarat.", "analyst")
]

@pytest.mark.parametrize("query,expected_brain", ROUTER_BENCHMARKS)
def test_router_intent_dispatch(query, expected_brain):
    decision = auto_route_query(query)
    assert decision.target_brain == expected_brain, (
        f"Query '{query}' routed to '{decision.target_brain}', expected '{expected_brain}'"
    )
    assert decision.confidence_score >= 0.85
```

---

### 3.3 Suite 3: PostGIS Spatial Intersection & Vector Tests
Validates spatial queries against test district boundaries and artificial hazard polygons.

```python
# test_gis_operations.py
import pytest
from app.gis.service import intersect_hazard_polygon

def test_hazard_district_intersection(db_session):
    """Verifies that an artificial hazard polygon over Surat district correctly calculates area."""
    surat_hazard_geojson = {
        "type": "Polygon",
        "coordinates": [[[72.7, 21.1], [72.9, 21.1], [72.9, 21.3], [72.7, 21.3], [72.7, 21.1]]]
    }
    result = intersect_hazard_polygon(surat_hazard_geojson, db_session)
    assert len(result.intersected_districts) >= 1
    surat_hit = next(d for d in result.intersected_districts if d.name == "Surat")
    assert surat_hit.exposed_area_pct > 0.0
```

---

### 3.4 Suite 4: LLM Grounding & Hallucination Prevention Tests
Feeds controlled Evidence Packages with injected test values and asserts that output text contains exact numbers and no mutated warnings.

```python
# test_llm_grounding.py
import pytest
from app.llm.orchestrator import evaluate_grounding_fidelity

def test_llm_zero_hallucination_guarantee():
    evidence_package = {
        "forecast": {"temperature_max_c": 31.8, "rainfall_total_mm": 42.6},
        "official_alerts": [{"warning_color": "Orange", "hazard": "Heavy Rainfall"}]
    }
    generated_llm_response = {
        "summary": "Heavy rain of 42.6 mm expected tomorrow with high temperatures of 31.8°C.",
        "alert": {"level": "Orange", "hazard": "Heavy Rainfall"}
    }
    fidelity_report = evaluate_grounding_fidelity(evidence_package, generated_llm_response)
    assert fidelity_report.has_hallucinations is False
    assert fidelity_report.warning_preserved is True
```

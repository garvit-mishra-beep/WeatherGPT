# WeatherGPT — Domain Brains Implementation Specification

**Document:** `21_BRAINS_IMPLEMENTATION.md`  
**Status:** Approved Technical Specification  
**Primary Product Authority:** [docs/01_PRD.md](01_PRD.md)  
**Related Specs:** [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md), [03_LLM_BRAIN_SPEC.md](03_LLM_BRAIN_SPEC.md), [04_INPUT_OUTPUT_CONTRACT.md](04_INPUT_OUTPUT_CONTRACT.md), [05_TOOL_REGISTRY.md](05_TOOL_REGISTRY.md), [11_ANALYTICS_ENGINE.md](11_ANALYTICS_ENGINE.md), [12_PERSONALIZATION_SPEC.md](12_PERSONALIZATION_SPEC.md), [13_MULTILINGUAL_SPEC.md](13_MULTILINGUAL_SPEC.md), [15_ERROR_GUARDRAILS.md](15_ERROR_GUARDRAILS.md)

---

## 1. Executive Summary & Unified Architecture

WeatherGPT integrates four specialized Domain Brains sharing a single, standardized, tool-orchestrated and grounding-controlled reasoning pipeline:

```text
User Request Turn
       │
       ▼
[ContextManager] ──> [AutoRouter / Explicit Brain Resolver]
                            │
              ┌─────────────┼─────────────┬─────────────┐
              ▼             ▼             ▼             ▼
         GeneralBrain  FarmerBrain  ResearcherBrain AnalystBrain
              │             │             │             │
              └─────────────┼─────────────┴─────────────┘
                            │
                            ▼
              [LLM Tool-Calling Framework]
                            │
                            ▼
              [Tool Gateway (Authorized Tools)]
                            │
                            ▼
              [EvidenceBuilder (EvidencePackage)]
                            │
                            ▼
              [GroundingService (Validation & Bounded Retry)]
                            │
                            ▼
              [FinalResponseSchema & BrainResponse]
```

---

## 2. The Four Concrete Domain Brains

### 2.1 General Weather Brain (`GeneralBrain`)
* **Scope:** Everyday conversational weather, forecasts, temperature, precipitation probability, and official alerts.
* **Authorized Tools:** `get_forecast`, `resolve_location`.
* **Visualizations Emitted:** `weather_card` (current conditions, temperature, humidity, wind).
* **System Prompt:** Emphasizes plain language explanation and factual accuracy.

### 2.2 Farmer / Agriculture Brain (`FarmerBrain`)
* **Scope:** Agronomic decision intelligence (irrigation scheduling via FAO-56 $ET_0$, chemical spraying windows, crop risk, sowing/harvesting timing).
* **Authorized Tools:** `calculate_irrigation_advisory`, `get_forecast`, `resolve_location`, `run_risk_analysis`.
* **Personalization Integration:** Consumes crop name, growth stage, soil moisture % from `PersonalizationContext`.
* **Visualizations Emitted:** `chart` (`rainfall_irrigation_combo`).
* **Recommendations:** Emits structured `Recommendation(primary_action=IRRIGATE_NOW | POSTPONE_IRRIGATION, actions=[...])`.

### 2.3 Researcher / Climate Science Brain (`ResearcherBrain`)
* **Scope:** Multi-decadal historical climate trends (Mann-Kendall, Sen's slope), anomaly detection, and NWP model comparisons (GFS vs. ECMWF).
* **Authorized Tools:** `get_forecast`, `resolve_location`, `run_risk_analysis`.
* **Visualizations Emitted:** `chart` (`line` trend chart).
* **System Prompt:** Emphasizes scientific rigorousness, dataset provenance, and analytical limitations.

### 2.4 Analyst / Data Analysis Brain (`AnalystBrain`)
* **Scope:** Spatial hazard-exposure-vulnerability quantification, multi-district comparisons, disaster risk mitigation.
* **Authorized Tools:** `run_risk_analysis`, `get_forecast`, `resolve_location`.
* **Visualizations Emitted:** `map` (Spatial hazard overlay) and comparative tables.
* **Recommendations:** Emits structured operational risk alerts (`SUSPEND_OPERATIONS | PROCEED_WITH_CAUTION`).

---

## 3. Core Architectural Invariants

1. **The LLM is NOT the Meteorological Engine:** All factual figures originate from approved tools via the Tool Gateway.
2. **Warning Immutability:** Official IMD warning levels (Red, Orange, Yellow, Green) cannot be altered or downgraded.
3. **Multilingual Numerical Invariance:** Numerical figures ($33.2^\circ\text{C}$, $24.5\text{ mm}$) remain constant across all 5 Indian languages.
4. **Architectural Purity:** Domain brains contain zero direct database queries, raw API calls, or ad-hoc calculation algorithms.

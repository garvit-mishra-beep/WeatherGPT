# Ayushmaan Domain Brain Integration Architecture

**Document:** `docs/AYUSHMAAN_BRAIN_INTEGRATION.md`  
**Milestone:** P7.8 — Ayushmaan Brain Integration  
**Status:** Completed & Validated  
**Test Suite:** 713 Backend Tests + 131 Android Unit Tests (100% Pass Rate)

---

## 1. Executive Summary

WeatherGPT provides conversational weather intelligence and agricultural/hazard decision support for India. Teammate Ayushmaan contributed domain implementations in the `Ayushmaan/` directory, specifically featuring:
1. **Analyst Brain (`Ayushmaan/Analyst Brain/`):** A comprehensive 13-stage deterministic analytical engine with natural language understanding (NLU), meteorological quality control (QC), spatial hazard classification, multi-criteria decision analysis (MCDA) risk scoring, operational decision support, and cryptographic SHA-256 evidence provenance.
2. **Researcher Brain (`Ayushmaan/Rescearcher brain/`):** Statistical climate engines covering ETCCDI climate extreme indices, Mann-Kendall trend tests, Sen's slope estimator, SPI/SPEI drought indices, extreme value analysis (Gumbel/GEV return periods), and NWP model verification (RMSE/MAE/Brier score).
3. **Farmer Brain (`Ayushmaan/farmer brain/`):** Agricultural advisory rules covering FAO-56 crop water balance, spraying windows, phenological stage thermal risk, fertilizer application suitability, and pest/disease risk models.

This document details the unified architecture integrating Ayushmaan's domain logic cleanly behind WeatherGPT's canonical contracts, eliminating duplicate execution paths and ensuring strict numerical and multilingual invariance across all 10 supported Indian languages (`en`, `hi`, `mr`, `bn`, `ta`, `te`, `gu`, `kn`, `ml`, `pa`).

---

## 2. Architectural Integration Map

```
                     ┌───────────────────────────────┐
                     │   Android Jetpack Compose UI  │
                     │    (10 Indian Languages)      │
                     └──────────────┬────────────────┘
                                    │ HTTP /api/v1/chat
                                    ▼
                     ┌───────────────────────────────┐
                     │       FastAPI Gateway         │
                     │    AppContainer Resolution    │
                     └──────────────┬────────────────┘
                                    │
                                    ▼
                     ┌───────────────────────────────┐
                     │       BrainOrchestrator       │
                     │  Auto-Routing & Intent Class. │
                     └──────────────┬────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         ▼                          ▼                          ▼
┌──────────────────┐      ┌──────────────────┐       ┌──────────────────┐
│   GeneralBrain   │      │   AnalystBrain   │       │   FarmerBrain    │
│ (Surface / NWP)  │      │ (Risk & Decision)│       │(FAO-56 / Advisory│
└──────────────────┘      └─────────┬────────┘       └──────────────────┘
                                    │
                                    ▼
                     ┌──────────────────────────────┐
                     │   app.brains.analyst_core    │
                     │ ┌──────────────────────────┐ │
                     │ │ NLU & Intent Extraction  │ │
                     │ ├──────────────────────────┤ │
                     │ │ Real / CAP Warning Feeds │ │
                     │ ├──────────────────────────┤ │
                     │ │ Meteorological QC Filter │ │
                     │ ├──────────────────────────┤ │
                     │ │ Multi-Hazard Classifiers │ │
                     │ ├──────────────────────────┤ │
                     │ │ MCDA Risk Scoring Engine │ │
                     │ ├──────────────────────────┤ │
                     │ │ Operational Decision Supp│ │
                     │ ├──────────────────────────┤ │
                     │ │ SHA-256 Crypto Provenance│ │
                     │ └──────────────────────────┘ │
                     └──────────────┬───────────────┘
                                    │
                                    ▼
                     ┌──────────────────────────────┐
                     │     FinalResponseSchema      │
                     │  (Grounding & Localization)  │
                     └──────────────────────────────┘
```

---

## 3. Core Component Mapping

| Subsystem | Ayushmaan Module | WeatherGPT Integrated Module | Primary Invariant / Role |
| :--- | :--- | :--- | :--- |
| **Analyst Core Facade** | `analyst_brain.brain.analyst_brain` | `app.brains.analyst_core.brain.analyst_brain.AnalystBrain` | High-assurance deterministic facade coordinating the 13-stage pipeline |
| **Analyst Orchestrator** | `analyst_brain.brain.orchestrator` | `app.brains.analyst_core.brain.orchestrator.AnalystOrchestrator` | Sequential execution coordinator (Query $\to$ NLU $\to$ Fusion $\to$ QC $\to$ Hazard $\to$ Risk $\to$ Decision $\to$ Evidence) |
| **Operational Decision** | `analyst_brain.brain.decision_engine` | `app.brains.analyst_core.brain.decision_engine.DecisionEngine` | Evaluates verdicts: `GO`, `PROCEED_WITH_CAUTION`, `POSTPONE_OR_RELOCATE`, `NO_GO` |
| **Hazard Analyzer** | `analyst_brain.analysis.hazard` | `app.brains.analyst_core.analysis.hazard.HazardAnalyzer` | Detects 14 hazard types (Heavy Rain, Heatwave, Coldwave, Wind, Flash Flood, Compound) |
| **MCDA Risk Engine** | `analyst_brain.brain.risk_engine` | `app.brains.analyst_core.brain.risk_engine.RiskEngine` | Impact-based risk assessment: $\text{Hazard} \times \text{Exposure} \times \text{Vulnerability}$ |
| **Meteorological QC** | `analyst_brain.qc.quality_control` | `app.brains.analyst_core.qc.quality_control.MeteorologicalQC` | Physical limits, internal consistency, rate of change, and duplicate filtering |
| **Cryptographic Provenance**| `analyst_brain.evidence.provenance` | `app.brains.analyst_core.evidence.provenance.ProvenanceTracker` | SHA-256 content hashes, lineage trees, producing agency attribution |
| **Canonical WeatherGPT Brain**| — | `app.brains.analyst.AnalystBrain` | Implements `BaseBrain`, bridges `AnalystResult` into `FinalResponseSchema` |

---

## 4. Invariant Preservation & Non-Negotiable Rules

1. **The LLM is NOT the Source of Truth:**
   - Numerical observations, rainfall amounts, risk indices, and threshold crossings are calculated deterministically by pure Python engines before LLM synthesis.
2. **Official Warnings are Immutable:**
   - Official IMD and NDMA Sachet CAP alerts (`GREEN`, `YELLOW`, `ORANGE`, `RED`) cannot be downgraded, elevated, or invented.
3. **Cryptographic Provenance:**
   - Every analytical finding links to a traceable `EvidenceItem` with a verified `content_sha256` hash and producing agency metadata.
4. **Multilingual Numerical Invariance:**
   - Numbers (e.g., $85\text{ mm}$, $42^\circ\text{C}$, $65\text{ km/h}$) and scientific units are strictly invariant when translated across English, Hindi, Marathi, Bengali, Tamil, Telugu, Gujarati, Kannada, Malayalam, and Punjabi.
5. **No Competing Paths:**
   - Exactly one unified `AnalystBrain` exists in the system, dispatching directly to `app.brains.analyst_core` while maintaining compatibility with the versioned REST API (`/api/v1/chat`).

---

## 5. Verification & Test Coverage Summary

- **Adapted Analyst Core Unit Tests (`tests/analyst_core/`):** 138 passed (100%)
- **Integrated Analyst Brain Tests (`tests/test_ayushmaan_analyst_integration.py`):** 3 passed (100%)
- **Full Backend Pytest Test Suite:** 713 passed, 21 skipped (100% pass rate)
- **Full Android Unit Test Suite:** 131 passed (100% pass rate)
- **Physical Device Validation (`US4L6H5HMNJZR8YT`):** Debug APK installed, app launched, UI responsive.

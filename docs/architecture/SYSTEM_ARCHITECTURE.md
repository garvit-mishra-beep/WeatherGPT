# VAYUBODHAK — CANONICAL SYSTEM ARCHITECTURE

**System**: VAYUBODHAK (वयुबोधक)  
**Classification**: Safety-Critical Hyperlocal Weather & Climate Decision Intelligence System  
**Architecture Paradigm**: Evidence-First Deterministic Pipeline with Isolated LLM Layer  

---

## 1. Core Architectural Principle

> **No Large Language Model exists in the critical disaster risk calculation or life-safety decision path.**

VAYUBODHAK strictly separates **deterministic mathematical calculation** from **generative linguistic synthesis**. All hazard thresholds, physical exposure assessments, damage vulnerability curves, quantitative risk formulations ($R = H \times E \times V$), localized potential impact mappings, and actionable operational advisories (**Nirnay**) are computed purely by deterministic Python engines and verified rule catalogs.

---

## 2. End-to-End Operational Pipeline Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   OPERATIONAL DATA SOURCES (Phase 9B)                  │
│  [Statutory: IMD, CWC, NDMA]  [Telemetry: Open-Meteo, OpenAQ, GFS, WRF]│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   METEOROLOGICAL ADAPTERS & GOVERNANCE                 │
│      Strict source classification (E0 Statutory vs E2 Supporting)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   EVIDENCE FOUNDATION (Phase 2A)                       │
│    Provenance, SHA-256 payload hashing, temporal windows, QC bounds    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               OPERATIONAL EVENT STREAMING (Phase 9C-B)                 │
│      Sequential ingestion, correlation IDs, idempotent deduplication   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      CHANGE DETECTOR (Phase 9C-B)                      │
│     Calibrated physical delta thresholds (e.g. 2.5mm rain, 64.5mm)     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               SELECTIVE RECALCULATION ENGINE (Phase 9C-C)              │
│  ┌──────────────────────────────┐    ┌───────────────────────────────┐ │
│  │   REUSE UNAFFECTED STAGES    │    │      RECOMPUTE AFFECTED       │ │
│  │  • Spatial Exposure (Roads)  │    │  • Dynamic Hazard (Intensity) │ │
│  │  • Vulnerability (Drainage)  │    │  • Quantitative Risk (H×E×V)  │ │
│  └──────────────────────────────┘    │  • Potential Impact (Damage)  │ │
│                                      │  • Decision Engine (Nirnay)   │ │
│                                      └───────────────────────────────┘ │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  DECISION REVISION ENGINE (Phase 9C-D)                 │
│         Immutable revision chaining (REV_1 -> REV_2 -> REV_3)          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
┌───────────────────────────────────┐ ┌──────────────────────────────────┐
│   NOTIFICATION ENGINE (Phase 9E)  │ │     OPERATIONAL SYNC API       │
│ Priority deduplication & dispatch │ │  Cursor handshake (cursor_seq)   │
└─────────────────┬─────────────────┘ └───────────────┬──────────────────┘
                  │                                   │
                  └─────────────────┬─────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   ANDROID CLIENT ARCHITECTURE (Phase 9C-A)             │
│  • SystemResilienceManager: Automatic OFFLINE / RECOVERING transitions │
│  • Room SQLite Database: Local persistent store for Nirnay & Events    │
│  • Failure-Aware UI: Zero masking of stale data; verified cache status │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Decoupled Conversational / Explanation Layer

The Generative AI layer is isolated and downstream of the deterministic pipeline:

```text
┌───────────────────────────────────┐
│     CANONICAL NIRNAY CARD         │
│  (Calculated Verdict, Action,     │
│   Why, Constraints, Citations)    │
└─────────────────┬─────────────────┘
                  │
                  ▼
┌───────────────────────────────────┐
│       STRUCTURED CONTEXT          │
│   (Domain Brain Prompt Injection) │
└─────────────────┬─────────────────┘
                  │
                  ▼
┌───────────────────────────────────┐
│      OPTIONAL LLM RUNTIME         │
│   (Local Ollama Gemma 2 2B /      │
│    Cloud Gemini 1.5 Flash)        │
└─────────────────┬─────────────────┘
                  │
                  ▼
┌───────────────────────────────────┐
│  EXPLANATION & LOCALIZATION       │
│  • Natural language responses     │
│  • Hindi / English translation    │
│  • Agronomic query expansion      │
└───────────────────────────────────┘
```

**Failure Guarantees**:
* If the LLM is unreachable, offline, or returns invalid syntax, the system falls back gracefully to template-driven summaries rendered directly from `NirnayCard.why` and `NirnayCard.recommended_action`.
* Under no circumstances can an LLM hallucination downgrade an active Red Warning or alter computed risk indices.

---

## 4. The Four Domain Brains

1. **General Brain**:
   * Communicates everyday atmospheric conditions, temperature comfort, and broad activity suitability in conversational Hindi and English.
2. **Farmer Brain (Krishi Buddhi)**:
   * Translates meteorological observations into agronomic decisions: crop-specific spray suitability, irrigation requirement ($ET_0$ calculation via FAO-56 Penman-Monteith), and harvest windows.
3. **Researcher Brain (Anusandhan Buddhi)**:
   * Provides deep scientific provenance, Mann-Kendall climate trends, historical baseline anomalies, and verifiable citations back to the Evidence Foundation.
4. **Analyst Brain (Visleshak Buddhi)**:
   * Evaluates spatial hazard intersections, multi-model ensemble spread (GFS vs WRF vs ECMWF), critical asset vulnerability, and disaster response logistics.

---

## 5. Security & Source Governance Boundaries

* **E0 / E1 Statutory Authorities**: Only officially constituted government bodies (IMD, CWC, NDMA) are legally permitted to issue official alerts.
* **E2 Supporting Telemetry**: Numerical models and third-party APIs (Open-Meteo, OpenAQ, GFS) are classified as non-authoritative telemetry.
* **Role-Based Access Control (RBAC)**: All administrative and scenario control endpoints are protected by cryptographic token verification.

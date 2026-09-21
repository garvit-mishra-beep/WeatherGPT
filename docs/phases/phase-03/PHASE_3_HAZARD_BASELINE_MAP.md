# Phase 3 — Hazard Baseline Map

## Purpose

This document maps the existing VAYUBODHAK hazard logic discovered during
the Phase 3 forensic audit, identifying what existed before Phase 3, and
how it is positioned relative to the new deterministic hazard engine.

---

## Pre-Phase 3 Hazard Logic Inventory

### System 1: GIS Analysis Layer

**Location:** `app/gis/analysis/hazards.py`

| Function | Hazard Type | Thresholds | Evidence Integration |
|---|---|---|---|
| `score_rainfall_rate_hazard()` | Rainfall | ≥5, ≥20, ≥50 mm/h | ❌ Raw float input |
| `score_wind_hazard()` | Wind | ≥40, ≥62, ≥89 km/h | ❌ Raw float input |
| `score_temperature_hazard()` | Heat/Cold | ≥40/≤10°C | ❌ Raw float input |
| `score_official_alert_hazard()` | Official Alert | Green/Yellow/Orange/Red | ❌ Raw string input |

**Output:** Numeric 0-10 hazard score  
**Provenance:** None  
**Quality Gating:** None  
**Rule Versioning:** None  

### System 2: Analyst Core HazardAnalyzer

**Location:** `app/brains/analyst_core/analysis/hazard.py`

| Hazard Module | Thresholds | Source | Basis |
|---|---|---|---|
| Heavy Rainfall | 64.5 / 115.6 / 204.5 mm (24h) | IMD 2024 | Official |
| Flood (Hydrological) | API + burst + riverine + soil moisture | Engineering heuristic | Prototype |
| Heatwave | 40°C (plains) / 45°C (severe) | IMD | Official |
| Cyclone | IMD 8-stage scale + pressure drop | IMD | Official |
| Lightning | CAPE ≥1000/≥2500, LI ≤-3/≤-6 | WMO diagnostic | Engineering |
| Cold Wave | ≤10°C / ≤4°C | IMD | Official |
| Dense Fog | ≤500 / ≤200 / ≤50 m | IMD | Official |
| Compound Hazards | Rain+Soil, Heat+Humidity, Wind+Rain | Engineering | Prototype |

**Output:** Tuple[List[HazardType], float, List[str]]  
**Provenance:** None (evidence strings generated inline)  
**Quality Gating:** None  
**Rule Versioning:** ThresholdConfig (IMD-MET-2024.1) — versioned but not per-rule  

### System 3: Proactive Service

**Location:** `app/proactive/service.py`

| Check | Threshold | Source |
|---|---|---|
| Rain alert | ≥35.5 mm | Approximate IMD |
| Heat alert | ≥40°C | IMD |
| Wind alert | ≥35 km/h | Below IMD strong wind |

**Output:** Push notification event  
**Provenance:** Partial (uses evidence_builder, but not Phase 2A EvidenceRecord)  
**Quality Gating:** None  

---

## Phase 2A Foundation (Available for Phase 3)

| Component | Status | Location |
|---|---|---|
| EvidenceRecord | ✅ Canonical, immutable | `app/evidence/models.py` |
| EvidenceService | ✅ create/derive/verify/bundle | `app/evidence/service.py` |
| SourceRegistry | ✅ 8 canonical sources (E0-E5) | `app/evidence/registry.py` |
| ClaimGate | ✅ APPROVED/DRAFT/RETIRED lifecycle | `app/evidence/claim_gate.py` |
| QualityState | ✅ VALID/MISSING/STALE/INVALID/CONFLICT | `app/evidence/models.py` |
| FreshnessPolicy | ✅ Class-specific staleness rules | `app/evidence/models.py` |

---

## Phase 3 Integration Strategy

The Phase 3 `app/hazard/` module:

1. **Consumes** Phase 2A EvidenceRecords as input
2. **Applies** deterministic rules (from HazardRuleRegistry) with explicit basis types
3. **Produces** HazardEvaluation results with full provenance
4. **Registers** hazard claims in the Phase 2A ClaimRegistry
5. **Does NOT modify** existing Systems 1-3

Existing subsystems continue to function independently. Future phases
can wire them to delegate to the new `HazardEngine` for evidence-linked evaluation.

---

## Type System Reconciliation

| Phase 3 HazardType | Analyst Core Equivalent | GIS Equivalent |
|---|---|---|
| HEAVY_RAINFALL | HEAVY_RAINFALL | HEAVY_RAINFALL |
| HEAT | EXTREME_HEAT | HEAT_WAVE |
| FLOOD | FLOODING / FLASH_FLOOD | FLOOD_INUNDATION |
| CYCLONE | CYCLONE | CYCLONE_STORM |
| STRONG_WIND | STRONG_WIND | STRONG_WIND |
| LIGHTNING | LIGHTNING / THUNDERSTORM | — |
| FOG | FOG_POOR_VISIBILITY | — |
| COLD_WAVE | EXTREME_COLD | — |
| LANDSLIDE_SUSCEPTIBILITY | — | — |
| OFFICIAL_WARNING | (inline) | — |
| COMPOUND | COMPOUND_HAZARD | (MultiHazardResult) |

The Phase 3 type system is the canonical evidence-linked taxonomy.
Existing type systems are preserved for backward compatibility.

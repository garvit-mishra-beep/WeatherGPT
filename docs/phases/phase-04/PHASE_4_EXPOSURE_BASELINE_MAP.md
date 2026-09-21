# Phase 4 — Exposure Baseline Map

## Purpose

This document maps the existing VAYUBODHAK codebase and database schemas prior to
implementing Phase 4 (Quantified Exposure Modeling), identifying existing logic,
data assets, reusable components, and gaps across all exposure domains.

---

## 1. Forensic Baseline Inventory

| Exposure Requirement | Existing Code / Data | Existing Schema | Source | Reusable? | Classification | Gap | Action |
|---|---|---|---|---|---|---|---|
| **Administrative Boundary Exposure** | `app/gis/analysis/exposure.py`, `app/gis/spatial/engine.py` | `spatial_states`, `spatial_districts`, `spatial_subdistricts` | Survey of India / Census / LGD | Yes | Operational | Only computes geometric area overlap %; lacks demographic data integration | Extend to link with administrative population figures |
| **Administrative Population** | None (prototype hardcoded values in `app/tools/catalog.py`) | None | Census of India 2011 baseline | No | Missing | No district/subdistrict population columns or demographic tables | Implement Census baseline dataset and Area-Weighted Administrative Population method |
| **Gridded Population** | Planned in `docs/09_GIS_SPEC.md` §2 (`exposure_population`) | None | WorldPop / LandScan | No | Placeholder / Missing | No raster table or grid cell model currently ingested | Define `GriddedPopulation` model, ingestion interface, and zonal aggregation method |
| **Buildings** | None | None | OpenStreetMap / Municipal GIS | No | Missing | No building footprint table or polygon intersection logic | Implement `BuildingFootprint` model and polygon intersection method |
| **Roads / Highways** | Planned in `docs/09_GIS_SPEC.md` §2 (`exposure_highways`) | None | OpenStreetMap / NHAI | No | Placeholder / Missing | No linear infrastructure table or metric length calculation | Implement `RoadSegment` model and metric geodesic length intersection |
| **Hospitals / Healthcare** | Mentioned in Phase 3 claim negative boundaries | None | MoHFW / OSM Healthcare | No | Missing | No point asset registry for hospitals | Implement unified `CriticalAsset` architecture with `HOSPITAL` type |
| **Schools / Education** | None | None | UDISE+ / OSM Education | No | Missing | No point asset registry for schools | Implement unified `CriticalAsset` architecture with `SCHOOL` type |
| **Police / Emergency Services** | None | None | State Police / NDMA / OSM | No | Missing | No point asset registry for emergency services | Implement unified `CriticalAsset` architecture with `POLICE_EMERGENCY` type |
| **Critical Infrastructure** (Power/Water/Telecom) | Planned in `app/contracts/personalization.py` list | None | State utilities / OSM | No | Missing | No unified infrastructure asset model | Implement unified `CriticalAsset` architecture supporting multiple subtypes |
| **Agriculture / Cropland** | `FarmerPlot` in `app/db/models/farmer.py` | `farmer_plots` (PostGIS Point, acreage, crop) | User-registered farmer plots | Yes | Incomplete | Plots are registered points with acreage; no regional ICAR crop zones polygon table | Reuse `FarmerPlot` for registered farm exposure; create cropland exposure model |

---

## 2. Reusable Foundations from Phase 2A & Phase 3

### Phase 2A Evidence Foundation
- **`EvidenceRecord`** (`app/evidence/models.py`): Immutable, SHA-256 hashed canonical record. Exposure assessments derive from hazard evidence and exposure dataset evidence.
- **`QualityState`** (`app/evidence/models.py`): `VALID`, `MISSING`, `STALE`, `INVALID`, `CONFLICT`. Zero silent conversions.
- **`ClaimGate`** (`app/evidence/claim_gate.py`): Enforces `APPROVED`, `DRAFT`, `RETIRED` lifecycle and rejects prohibited wording.
- **`SourceRegistry`** (`app/evidence/registry.py`): Authority levels E0–E5. Exposure datasets will cite official government statistical sources (E1/E2).

### Phase 3 Deterministic Hazard Modeling
- **`HazardEvaluation`** (`app/hazard/models.py`): Carries `hazard_id`, `hazard_type`, `severity`, `basis_type`, and `spatial_scope` / geometry.
- **`HazardState`** (`app/hazard/models.py`): Deterministic result consumed as the input footprint for exposure modeling.

### Existing Spatial Engine
- **PostGIS multi-tier administrative hierarchy**: `SpatialCountry`, `SpatialState`, `SpatialDistrict`, `SpatialSubDistrict`.
- **Spatial queries**: Geodesic area intersection (`ST_Intersection`, `ST_Area`), containment, proximity.

---

## 3. Methodological Guardrails

### Exposure ≠ Vulnerability ≠ Impact
- **Exposure**: "What people, assets, or land are located within the hazard footprint?"
- **Vulnerability**: "What is the degree of susceptibility of the exposed elements?" (Strictly out of Phase 4).
- **Impact**: "What damage, casualties, or economic disruption will occur?" (Strictly out of Phase 4).

### Population Estimation Guardrails
1. **Administrative Population**:
   - Area-weighted estimation assumes uniform distribution across administrative units unless gridded data exists.
   - Must be explicitly labeled as an **area-weighted administrative estimate**.
   - Must document formula, assumptions, limitations, and spatial resolution.
   - Must NEVER be presented as an exact live headcount.
2. **Gridded Population**:
   - Preserves native cell resolution (e.g. 100m, 1km).
   - Zonal summation of intersecting cells.
3. **Double-Counting Prevention**:
   - If both administrative and gridded data cover the same zone, the engine uses an explicit method priority rule.
   - **Under no circumstances are administrative and gridded population summed together.**

### Asset & Infrastructure Guardrails
- Intersected roads report `exposed_length_km` — **never** inferred as "closed" or "destroyed".
- Intersected hospitals report `exposed_count` — **never** inferred as "damaged" or "inoperable".
- Intersected croplands report `exposed_area_acres` — **never** inferred as "crop loss" or "economic damage".

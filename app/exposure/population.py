"""Population exposure modeling for VAYUBODHAK Phase 4.

Implements:
1. Area-Weighted Administrative Population Estimation (Census baseline)
2. Gridded Population Surface Zonal Summation (e.g. WorldPop 1km)
3. Anti-Double-Counting Methodology Selector
"""

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from app.evidence.models import QualityState
from app.exposure.models import (
    AdministrativePopulationRecord,
    ExposureResult,
    ExposureType,
    GriddedPopulationCell,
    SpatialResolution,
    UncertaintyMetadata,
)
from app.exposure.spatial import (
    bbox_intersects,
    compute_bbox,
    compute_polygon_intersection_area_sqkm,
    point_in_polygon,
    spherical_polygon_area_sqkm,
)


# ============================================================================
# 1. Area-Weighted Administrative Population Estimation
# ============================================================================

def estimate_administrative_population_exposure(
    hazard_id: str,
    hazard_polygon: List[Tuple[float, float]],
    admin_record: AdministrativePopulationRecord,
    admin_polygon: List[Tuple[float, float]],
    method_version: str = "1.0.0",
) -> ExposureResult:
    """Calculates area-weighted estimated exposed population within an administrative unit.

    Formula:
        Exposed_Population = Total_Population * (Intersection_Area / Total_Area)
    """
    total_area = admin_record.total_area_sqkm
    if total_area <= 0.0:
        total_area = spherical_polygon_area_sqkm(admin_polygon)

    # Compute overlapping area
    intersect_area = compute_polygon_intersection_area_sqkm(admin_polygon, hazard_polygon)
    overlap_fraction = min(1.0, max(0.0, intersect_area / total_area)) if total_area > 0 else 0.0

    estimated_exposed_pop = round(admin_record.total_population * overlap_fraction, 1)

    uncertainty = UncertaintyMetadata(
        methodology="area-weighted administrative estimate",
        spatial_resolution=SpatialResolution.ADMINISTRATIVE_POLYGON,
        assumptions=[
            "Population is assumed uniformly distributed across the administrative unit.",
            "Demographic figures represent Census of India 2011 baseline data.",
        ],
        limitations=[
            "Uniformity assumption ignores urban centers, uninhabited forests, and terrain clustering.",
            "Historical baseline does not reflect post-2011 urbanization or seasonal migration.",
            "Cannot be used as an exact live headcount for evacuation logistics.",
        ],
        confidence_bounds={
            "lower_bound": round(estimated_exposed_pop * 0.70, 1),
            "upper_bound": round(estimated_exposed_pop * 1.30, 1),
        },
        is_estimate=True,
    )

    prov_payload = {
        "hazard_id": hazard_id,
        "admin_code": admin_record.admin_code,
        "total_population": admin_record.total_population,
        "total_area_sqkm": total_area,
        "intersect_area_sqkm": intersect_area,
        "overlap_fraction": overlap_fraction,
        "method_id": "EXP-METH-POP-ADMIN-001",
    }
    prov_hash = hashlib.sha256(json.dumps(prov_payload, sort_keys=True).encode()).hexdigest()

    exposure_id = f"EXP-POP-ADMIN-{admin_record.admin_code}-{prov_hash[:12]}"

    return ExposureResult(
        exposure_id=exposure_id,
        hazard_id=hazard_id,
        exposure_type=ExposureType.POPULATION_ADMIN,
        quantity=estimated_exposed_pop,
        unit="persons (area-weighted estimate)",
        location={
            "admin_code": admin_record.admin_code,
            "admin_name": admin_record.admin_name,
            "admin_level": admin_record.admin_level,
        },
        asset_identifiers=[admin_record.admin_code],
        source_id=admin_record.source_id,
        source_version=admin_record.source_version,
        spatial_resolution=SpatialResolution.ADMINISTRATIVE_POLYGON,
        quality_state=admin_record.quality_state,
        uncertainty=uncertainty,
        evidence_ids=[],
        provenance_id=prov_hash,
        method_id="EXP-METH-POP-ADMIN-001",
        method_version=method_version,
        derived_from=[hazard_id, admin_record.admin_code],
        intersection_area_sqkm=round(intersect_area, 2),
        total_area_sqkm=round(total_area, 2),
        overlap_fraction=round(overlap_fraction, 4),
        breakdown_details={
            "admin_population_total": admin_record.total_population,
            "census_year": admin_record.census_year,
            "is_historical": admin_record.is_historical,
            "methodology_label": "area-weighted administrative estimate",
        },
    )


# ============================================================================
# 2. Gridded Population Surface Zonal Summation
# ============================================================================

def estimate_gridded_population_exposure(
    hazard_id: str,
    hazard_polygon: List[Tuple[float, float]],
    cells: List[GriddedPopulationCell],
    method_version: str = "1.0.0",
) -> ExposureResult:
    """Calculates exposed population by summing intersecting raster/mesh grid cells."""
    hazard_bbox = compute_bbox(hazard_polygon)
    exposed_cells: List[GriddedPopulationCell] = []
    total_exposed_pop = 0.0

    for cell in cells:
        # Check bbox overlap
        if not bbox_intersects(cell.bbox, hazard_bbox):
            continue

        # Check cell centroid containment
        if point_in_polygon(cell.centroid_lon, cell.centroid_lat, hazard_polygon):
            exposed_cells.append(cell)
            total_exposed_pop += cell.population_count

    uncertainty = UncertaintyMetadata(
        methodology="gridded population surface zonal summation",
        spatial_resolution=SpatialResolution.POPULATION_GRID_CELL,
        assumptions=[
            "Dasymetric modeling accurately represents spatial population density.",
            "Cell centroid containment provides valid first-order zonal assignment.",
        ],
        limitations=[
            "Smoothing artifact in cell boundary edge clipping.",
            "Residential baseline does not account for transient daytime/commuter mobility.",
        ],
        confidence_bounds={
            "lower_bound": round(total_exposed_pop * 0.85, 1),
            "upper_bound": round(total_exposed_pop * 1.15, 1),
        },
        is_estimate=True,
    )

    cell_ids = [c.cell_id for c in exposed_cells]
    source_id = cells[0].source_id if cells else "SRC-WORLDPOP-GRID"
    source_version = cells[0].dataset_version if cells else "1.0"

    prov_payload = {
        "hazard_id": hazard_id,
        "exposed_cell_count": len(exposed_cells),
        "total_exposed_pop": total_exposed_pop,
        "cell_ids": cell_ids[:50],  # first 50 for hash
        "method_id": "EXP-METH-POP-GRID-001",
    }
    prov_hash = hashlib.sha256(json.dumps(prov_payload, sort_keys=True).encode()).hexdigest()
    exposure_id = f"EXP-POP-GRID-{prov_hash[:12]}"

    return ExposureResult(
        exposure_id=exposure_id,
        hazard_id=hazard_id,
        exposure_type=ExposureType.POPULATION_GRIDDED,
        quantity=round(total_exposed_pop, 1),
        unit="persons (gridded surface estimate)",
        location={"grid_resolution_meters": cells[0].resolution_meters if cells else 1000.0},
        asset_identifiers=cell_ids,
        source_id=source_id,
        source_version=source_version,
        spatial_resolution=SpatialResolution.POPULATION_GRID_CELL,
        quality_state=QualityState.VALID if cells else QualityState.MISSING,
        uncertainty=uncertainty,
        evidence_ids=[],
        provenance_id=prov_hash,
        method_id="EXP-METH-POP-GRID-001",
        method_version=method_version,
        derived_from=[hazard_id] + cell_ids[:20],
        breakdown_details={
            "exposed_cells_count": len(exposed_cells),
            "resolution_meters": cells[0].resolution_meters if cells else 1000.0,
            "methodology_label": "gridded population surface zonal summation",
        },
    )


# ============================================================================
# 3. Anti-Double-Counting Population Policy
# ============================================================================

def resolve_population_exposure(
    hazard_id: str,
    hazard_polygon: List[Tuple[float, float]],
    admin_records: Optional[List[Tuple[AdministrativePopulationRecord, List[Tuple[float, float]]]]] = None,
    gridded_cells: Optional[List[GriddedPopulationCell]] = None,
    preferred_method: str = "AUTO",
) -> List[ExposureResult]:
    """Resolves population exposure strictly preventing double counting.

    Policy:
    - Under NO circumstances are administrative and gridded populations summed.
    - If gridded data is available and preferred/AUTO: gridded method is applied.
    - Otherwise: administrative area-weighted method is applied.
    """
    results: List[ExposureResult] = []

    has_gridded = bool(gridded_cells)
    has_admin = bool(admin_records)

    if not has_gridded and not has_admin:
        # Both missing
        uncertainty = UncertaintyMetadata(
            methodology="none (data unavailable)",
            spatial_resolution=SpatialResolution.ADMINISTRATIVE_POLYGON,
            assumptions=[],
            limitations=["No population datasets available for the hazard footprint."],
            is_estimate=True,
        )
        results.append(
            ExposureResult(
                exposure_id=f"EXP-POP-MISSING-{hazard_id[:8]}",
                hazard_id=hazard_id,
                exposure_type=ExposureType.POPULATION,
                quantity=0.0,
                unit="persons",
                source_id="UNKNOWN",
                source_version="0.0",
                spatial_resolution=SpatialResolution.ADMINISTRATIVE_POLYGON,
                quality_state=QualityState.MISSING,
                uncertainty=uncertainty,
                provenance_id=hashlib.sha256(f"missing-{hazard_id}".encode()).hexdigest(),
                method_id="EXP-METH-POP-NONE",
                method_version="1.0.0",
            )
        )
        return results

    if (preferred_method == "GRIDDED" or (preferred_method == "AUTO" and has_gridded)) and gridded_cells:
        grid_res = estimate_gridded_population_exposure(hazard_id, hazard_polygon, gridded_cells)
        results.append(grid_res)
    elif admin_records:
        for admin_rec, admin_poly in admin_records:
            admin_res = estimate_administrative_population_exposure(
                hazard_id, hazard_polygon, admin_rec, admin_poly
            )
            if admin_res.quantity > 0:
                results.append(admin_res)

    return results

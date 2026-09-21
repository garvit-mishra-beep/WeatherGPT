"""Asset, infrastructure, and agricultural exposure modeling for VAYUBODHAK Phase 4.

Implements deterministic spatial exposure quantification for:
1. Critical Point Assets (Hospitals, Schools, Police/Emergency, Utilities)
2. Linear Transport Infrastructure (Roads / Highways)
3. Building Footprint Polygons
4. Agricultural Cropland & Farm Plots
"""

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from app.evidence.models import QualityState
from app.exposure.models import (
    BuildingFootprint,
    CriticalAsset,
    ExposureResult,
    ExposureType,
    RoadSegment,
    SpatialResolution,
    UncertaintyMetadata,
)
from app.exposure.spatial import (
    clip_linestring_with_polygon,
    compute_bbox,
    compute_polygon_intersection_area_sqkm,
    point_in_polygon,
)


# ============================================================================
# 1. Critical Point Infrastructure (Hospitals, Schools, Emergency Services)
# ============================================================================

def evaluate_point_asset_exposure(
    hazard_id: str,
    hazard_polygon: List[Tuple[float, float]],
    assets: List[CriticalAsset],
    target_type: Optional[ExposureType] = None,
    method_version: str = "1.0.0",
) -> List[ExposureResult]:
    """Identifies physical point assets contained within the hazard footprint.

    CRITICAL RULE:
        Does NOT infer operational status, service disruption, structural
        vulnerability, casualty risk, or patient capacity impact.
    """
    results: List[ExposureResult] = []
    filtered = [a for a in assets if target_type is None or a.asset_type == target_type]

    # Group by asset_type
    by_type: Dict[ExposureType, List[CriticalAsset]] = {}
    for a in filtered:
        by_type.setdefault(a.asset_type, []).append(a)

    for asset_type, type_assets in by_type.items():
        intersected_assets: List[CriticalAsset] = []
        for asset in type_assets:
            if point_in_polygon(asset.longitude, asset.latitude, hazard_polygon):
                intersected_assets.append(asset)

        if not intersected_assets:
            continue

        asset_ids = [a.asset_id for a in intersected_assets]
        asset_names = [a.name for a in intersected_assets]

        uncertainty = UncertaintyMetadata(
            methodology="point-in-polygon containment",
            spatial_resolution=SpatialResolution.POINT,
            assumptions=[
                "Point coordinates accurately pinpoint the asset facility location.",
            ],
            limitations=[
                "Campus perimeters or auxiliary service lines are not captured by single-point representation.",
                "Exposure signifies physical presence inside the footprint, NOT damage or functional disruption.",
            ],
            is_estimate=False,
        )

        prov_payload = {
            "hazard_id": hazard_id,
            "asset_type": asset_type.value,
            "intersected_asset_ids": asset_ids,
            "method_id": "EXP-METH-ASSET-POINT-001",
        }
        prov_hash = hashlib.sha256(json.dumps(prov_payload, sort_keys=True).encode()).hexdigest()
        exposure_id = f"EXP-{asset_type.value}-{prov_hash[:12]}"

        source_id = intersected_assets[0].source_id
        source_version = intersected_assets[0].source_version

        results.append(
            ExposureResult(
                exposure_id=exposure_id,
                hazard_id=hazard_id,
                exposure_type=asset_type,
                quantity=float(len(intersected_assets)),
                unit="count",
                location={"intersected_count": len(intersected_assets)},
                asset_identifiers=asset_ids,
                source_id=source_id,
                source_version=source_version,
                spatial_resolution=SpatialResolution.POINT,
                quality_state=QualityState.VALID,
                uncertainty=uncertainty,
                evidence_ids=[],
                provenance_id=prov_hash,
                method_id="EXP-METH-ASSET-POINT-001",
                method_version=method_version,
                derived_from=[hazard_id] + asset_ids,
                breakdown_details={
                    "asset_names": asset_names,
                    "asset_types": [a.asset_type.value for a in intersected_assets],
                    "asset_metadata": [a.metadata for a in intersected_assets],
                },
            )
        )

    return results


# ============================================================================
# 2. Linear Transport Infrastructure (Roads / Highways)
# ============================================================================

def evaluate_road_exposure(
    hazard_id: str,
    hazard_polygon: List[Tuple[float, float]],
    roads: List[RoadSegment],
    method_version: str = "1.0.0",
) -> Optional[ExposureResult]:
    """Quantifies kilometers of road centerline passing through the hazard polygon.

    CRITICAL RULE:
        Exposure != disruption. Intersecting a hazard footprint does NOT mean
        the highway is flooded, washed out, closed, or impassable.
    """
    if not roads:
        return None

    exposed_roads: List[Tuple[RoadSegment, float]] = []
    total_exposed_km = 0.0

    for road in roads:
        clipped_len = clip_linestring_with_polygon(road.coordinates, hazard_polygon)
        if clipped_len > 0.0:
            exposed_roads.append((road, clipped_len))
            total_exposed_km += clipped_len

    if not exposed_roads:
        return None

    road_ids = [r[0].road_id for r in exposed_roads]
    classifications = list({r[0].road_classification for r in exposed_roads})

    uncertainty = UncertaintyMetadata(
        methodology="line-polygon geodesic clipping",
        spatial_resolution=SpatialResolution.ROAD_SEGMENT,
        assumptions=[
            "Road centerlines reflect standard surface alignment.",
        ],
        limitations=[
            "Elevated flyovers, bridges, or tunnels are not topographically differentiated.",
            "Does not assess road accessibility, traffic flow, pavement damage, or closure status.",
        ],
        confidence_bounds={
            "lower_bound": round(total_exposed_km * 0.95, 2),
            "upper_bound": round(total_exposed_km * 1.05, 2),
        },
        is_estimate=True,
    )

    prov_payload = {
        "hazard_id": hazard_id,
        "total_exposed_km": round(total_exposed_km, 3),
        "road_ids": road_ids,
        "method_id": "EXP-METH-INFRA-ROAD-001",
    }
    prov_hash = hashlib.sha256(json.dumps(prov_payload, sort_keys=True).encode()).hexdigest()
    exposure_id = f"EXP-ROAD-{prov_hash[:12]}"

    source_id = roads[0].source_id
    source_version = roads[0].source_version

    return ExposureResult(
        exposure_id=exposure_id,
        hazard_id=hazard_id,
        exposure_type=ExposureType.ROAD,
        quantity=round(total_exposed_km, 2),
        unit="km",
        location={"exposed_road_count": len(exposed_roads)},
        asset_identifiers=road_ids,
        source_id=source_id,
        source_version=source_version,
        spatial_resolution=SpatialResolution.ROAD_SEGMENT,
        quality_state=QualityState.VALID,
        uncertainty=uncertainty,
        evidence_ids=[],
        provenance_id=prov_hash,
        method_id="EXP-METH-INFRA-ROAD-001",
        method_version=method_version,
        derived_from=[hazard_id] + road_ids,
        breakdown_details={
            "road_classifications": classifications,
            "segments": [
                {
                    "road_id": r[0].road_id,
                    "road_name": r[0].road_name,
                    "classification": r[0].road_classification,
                    "total_length_km": r[0].length_km,
                    "exposed_length_km": round(r[1], 2),
                }
                for r in exposed_roads
            ],
        },
    )


# ============================================================================
# 3. Building Footprint Polygons
# ============================================================================

def evaluate_building_exposure(
    hazard_id: str,
    hazard_polygon: List[Tuple[float, float]],
    buildings: List[BuildingFootprint],
    method_version: str = "1.0.0",
) -> Optional[ExposureResult]:
    """Quantifies intersecting building structures and footprint surface area.

    CRITICAL RULE:
        Does NOT infer building occupancy, collapse risk, wall failure,
        structural vulnerability, or economic asset loss.
    """
    if not buildings:
        return None

    exposed_buildings: List[BuildingFootprint] = []
    total_footprint_sqm = 0.0

    for b in buildings:
        # Check first coordinate ring
        if b.coordinates:
            outer_ring = b.coordinates[0]
            # Fast check centroid/first vertex or polygon overlap
            if outer_ring and point_in_polygon(outer_ring[0][0], outer_ring[0][1], hazard_polygon):
                exposed_buildings.append(b)
                total_footprint_sqm += b.footprint_area_sqm
            else:
                inter_area = compute_polygon_intersection_area_sqkm(outer_ring, hazard_polygon)
                if inter_area > 0:
                    exposed_buildings.append(b)
                    total_footprint_sqm += b.footprint_area_sqm

    if not exposed_buildings:
        return None

    building_ids = [b.building_id for b in exposed_buildings]

    uncertainty = UncertaintyMetadata(
        methodology="building footprint polygon intersection",
        spatial_resolution=SpatialResolution.BUILDING_FOOTPRINT,
        assumptions=[
            "Footprints accurately capture structural roofline/ground boundaries.",
        ],
        limitations=[
            "Does not account for multi-story vertical density or basement presence.",
            "Building occupancy rates are completely unknown in Phase 4 exposure.",
        ],
        is_estimate=False,
    )

    prov_payload = {
        "hazard_id": hazard_id,
        "building_count": len(exposed_buildings),
        "total_footprint_sqm": total_footprint_sqm,
        "building_ids": building_ids[:50],
        "method_id": "EXP-METH-ASSET-POLY-001",
    }
    prov_hash = hashlib.sha256(json.dumps(prov_payload, sort_keys=True).encode()).hexdigest()
    exposure_id = f"EXP-BLD-{prov_hash[:12]}"

    source_id = buildings[0].source_id
    source_version = buildings[0].source_version

    return ExposureResult(
        exposure_id=exposure_id,
        hazard_id=hazard_id,
        exposure_type=ExposureType.BUILDING,
        quantity=float(len(exposed_buildings)),
        unit="count",
        location={"total_footprint_area_sqm": round(total_footprint_sqm, 1)},
        asset_identifiers=building_ids,
        source_id=source_id,
        source_version=source_version,
        spatial_resolution=SpatialResolution.BUILDING_FOOTPRINT,
        quality_state=QualityState.VALID,
        uncertainty=uncertainty,
        evidence_ids=[],
        provenance_id=prov_hash,
        method_id="EXP-METH-ASSET-POLY-001",
        method_version=method_version,
        derived_from=[hazard_id] + building_ids[:20],
        breakdown_details={
            "building_count": len(exposed_buildings),
            "total_footprint_area_sqm": round(total_footprint_sqm, 1),
            "uses_represented": list({b.building_use for b in exposed_buildings}),
        },
    )


# ============================================================================
# 4. Agricultural Plots & Cropland
# ============================================================================

def evaluate_agricultural_exposure(
    hazard_id: str,
    hazard_polygon: List[Tuple[float, float]],
    plots: List[Any],  # e.g. FarmerPlot or plot dictionaries
    method_version: str = "1.0.0",
) -> Optional[ExposureResult]:
    """Identifies cultivated farm plots falling within the hazard boundary.

    CRITICAL RULE:
        Does NOT estimate crop yield loss, lodging, submergence damage,
        or financial revenue loss.
    """
    if not plots:
        return None

    exposed_plots: List[Any] = []
    total_acres = 0.0
    crop_breakdown: Dict[str, float] = {}

    for p in plots:
        lon = getattr(p, "centroid_lon", None) or p.get("centroid_lon")
        lat = getattr(p, "centroid_lat", None) or p.get("centroid_lat")
        acres = getattr(p, "area_acres", None) or p.get("area_acres", 0.0) or 0.0
        crop = getattr(p, "crop_name", None) or p.get("crop_name", "Unknown")

        if lon is not None and lat is not None:
            if point_in_polygon(lon, lat, hazard_polygon):
                exposed_plots.append(p)
                total_acres += float(acres)
                crop_breakdown[crop] = crop_breakdown.get(crop, 0.0) + float(acres)

    if not exposed_plots:
        return None

    plot_ids = [
        str(getattr(p, "plot_id", None) or p.get("plot_id"))
        for p in exposed_plots
    ]

    uncertainty = UncertaintyMetadata(
        methodology="agricultural plot spatial containment",
        spatial_resolution=SpatialResolution.POINT,
        assumptions=[
            "Plot centroids and declared acreage reflect actively planted crops.",
        ],
        limitations=[
            "Fallow or unharvested portions of parcels are not verified by satellite in Phase 4.",
            "Exposure indicates geographic footprint overlap, NOT agricultural crop damage.",
        ],
        is_estimate=True,
    )

    prov_payload = {
        "hazard_id": hazard_id,
        "plot_count": len(exposed_plots),
        "total_acres": round(total_acres, 2),
        "plot_ids": plot_ids,
        "method_id": "EXP-METH-AGRI-PLOT-001",
    }
    prov_hash = hashlib.sha256(json.dumps(prov_payload, sort_keys=True).encode()).hexdigest()
    exposure_id = f"EXP-AGRI-{prov_hash[:12]}"

    return ExposureResult(
        exposure_id=exposure_id,
        hazard_id=hazard_id,
        exposure_type=ExposureType.AGRICULTURE,
        quantity=round(total_acres, 2),
        unit="acres",
        location={"exposed_plot_count": len(exposed_plots)},
        asset_identifiers=plot_ids,
        source_id="SRC-FARMER-REGISTRY",
        source_version="1.0",
        spatial_resolution=SpatialResolution.POINT,
        quality_state=QualityState.VALID,
        uncertainty=uncertainty,
        evidence_ids=[],
        provenance_id=prov_hash,
        method_id="EXP-METH-AGRI-PLOT-001",
        method_version=method_version,
        derived_from=[hazard_id] + plot_ids[:20],
        breakdown_details={
            "exposed_plots_count": len(exposed_plots),
            "total_acres": round(total_acres, 2),
            "crop_acreage_breakdown": {k: round(v, 2) for k, v in crop_breakdown.items()},
        },
    )

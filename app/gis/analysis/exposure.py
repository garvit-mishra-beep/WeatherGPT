"""Deterministic Spatial Exposure Quantification Engine.

Calculates geodesic overlapping area (km²), boundary exposure percentage, and normalized exposure score E.
"""

from typing import List, Optional
from app.gis.analysis.errors import ExposureCalculationError
from app.gis.analysis.types import ExposureMetrics
from app.gis.spatial.types import IntersectionMatch


def calculate_exposure_metrics(
    exposed_area_sqkm: float,
    total_area_sqkm: Optional[float] = None,
    affected_boundaries_count: int = 1,
) -> ExposureMetrics:
    """Calculates spatial exposure metrics and normalizes exposure index E in [0.0, 10.0].

    Args:
        exposed_area_sqkm: Geodesic overlapping area in km².
        total_area_sqkm: Total administrative area in km² (optional).
        affected_boundaries_count: Number of administrative units overlapping.

    Returns:
        ExposureMetrics: Area, percentage overlap, and normalized exposure score.
    """
    if exposed_area_sqkm < 0.0:
        raise ExposureCalculationError(f"Exposed area ({exposed_area_sqkm}) cannot be negative")

    if total_area_sqkm and total_area_sqkm > 0.0:
        pct = min(100.0, (exposed_area_sqkm / total_area_sqkm) * 100.0)
    else:
        # If total area is unpopulated, estimate percentage based on nominal district size (~3,500 km²)
        pct = min(100.0, (exposed_area_sqkm / 3500.0) * 100.0) if exposed_area_sqkm > 0 else 0.0

    # Normalized Exposure Score E in [0.0, 10.0]
    # 100% boundary exposure corresponds to E = 10.0
    exposure_score = round(min(10.0, pct / 10.0), 2)

    return ExposureMetrics(
        exposed_area_sqkm=round(exposed_area_sqkm, 2),
        exposed_area_pct=round(pct, 1),
        affected_boundaries_count=affected_boundaries_count,
        exposure_score=exposure_score,
        is_estimated=total_area_sqkm is None,
    )


def summarize_boundary_intersections(matches: List[IntersectionMatch]) -> ExposureMetrics:
    """Summarizes a list of PostGIS IntersectionMatch records into composite ExposureMetrics."""
    if not matches:
        return ExposureMetrics(
            exposed_area_sqkm=0.0,
            exposed_area_pct=0.0,
            affected_boundaries_count=0,
            exposure_score=0.0,
            is_estimated=False,
        )

    total_exposed_km2 = sum(m.exposed_area_sqkm for m in matches)
    max_overlap_pct = max(m.exposed_area_pct for m in matches)

    exposure_score = round(min(10.0, max_overlap_pct / 10.0), 2)

    return ExposureMetrics(
        exposed_area_sqkm=round(total_exposed_km2, 2),
        exposed_area_pct=round(max_overlap_pct, 1),
        affected_boundaries_count=len(matches),
        exposure_score=exposure_score,
        is_estimated=False,
    )

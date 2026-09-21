"""Core Exposure Engine for VAYUBODHAK Phase 4.

Coordinates deterministic spatial exposure quantification across population,
built assets, transport networks, and agriculture. Integrates with Phase 2A
Evidence Foundation and Phase 3 Deterministic Hazard Modeling.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from app.evidence.models import QualityState
from app.exposure.assets import (
    evaluate_agricultural_exposure,
    evaluate_building_exposure,
    evaluate_point_asset_exposure,
    evaluate_road_exposure,
)
from app.exposure.method_registry import exposure_method_registry
from app.exposure.models import (
    AdministrativePopulationRecord,
    BuildingFootprint,
    CriticalAsset,
    ExposureEvaluation,
    ExposureResult,
    ExposureType,
    GriddedPopulationCell,
    RoadSegment,
    SpatialResolution,
    UncertaintyMetadata,
)
from app.exposure.population import resolve_population_exposure
from app.exposure.spatial import (
    compute_bbox,
    compute_polygon_intersection_area_sqkm,
    spherical_polygon_area_sqkm,
)
from app.hazard.models import HazardEvaluation


class ExposureEngine:
    """Deterministic, spatially-grounded exposure quantification engine."""

    def __init__(self) -> None:
        self.registry = exposure_method_registry

    def evaluate(
        self,
        hazard_eval: HazardEvaluation,
        hazard_polygon: List[Tuple[float, float]],
        admin_population_records: Optional[List[Tuple[AdministrativePopulationRecord, List[Tuple[float, float]]]]] = None,
        gridded_population_cells: Optional[List[GriddedPopulationCell]] = None,
        point_assets: Optional[List[CriticalAsset]] = None,
        roads: Optional[List[RoadSegment]] = None,
        buildings: Optional[List[BuildingFootprint]] = None,
        agricultural_plots: Optional[List[Any]] = None,
        preferred_population_method: str = "AUTO",
    ) -> ExposureEvaluation:
        """Evaluates quantified exposure for an active hazard event footprint.

        CRITICAL CONSTRAINTS:
        1. Zero vulnerability, risk, impact, evacuation, or damage inferences.
        2. Strictly deterministic: same inputs produce identical results.
        3. Quality gating: surfaces MISSING, STALE, or INVALID dataset states.
        4. Anti-double-counting for population.
        """
        # Validate hazard polygon geometry
        if len(hazard_polygon) < 3:
            raise ValueError(
                f"Hazard polygon must contain at least 3 vertices, got {len(hazard_polygon)}"
            )

        hazard_id = hazard_eval.hazard_id
        hazard_type = hazard_eval.hazard_type.value if hasattr(hazard_eval.hazard_type, "value") else str(hazard_eval.hazard_type)
        eval_id = f"EXP-EVAL-{hazard_id[:12]}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        exposure_results: List[ExposureResult] = []
        quality_warnings: List[str] = []

        # 1. Evaluate Population Exposure
        pop_results = resolve_population_exposure(
            hazard_id=hazard_id,
            hazard_polygon=hazard_polygon,
            admin_records=admin_population_records,
            gridded_cells=gridded_population_cells,
            preferred_method=preferred_population_method,
        )
        for pr in pop_results:
            # Wire hazard evidence lineage
            pr.evidence_ids.extend(hazard_eval.evidence_ids)
            exposure_results.append(pr)
            if pr.quality_state in (QualityState.MISSING, QualityState.STALE, QualityState.INVALID):
                quality_warnings.append(f"Population dataset quality is {pr.quality_state.value}")

        # 2. Evaluate Critical Point Assets
        if point_assets:
            # Quality gate point assets
            valid_assets = [a for a in point_assets if a.quality_state == QualityState.VALID]
            invalid_count = len(point_assets) - len(valid_assets)
            if invalid_count > 0:
                quality_warnings.append(f"{invalid_count} critical assets rejected with INVALID coordinates")

            asset_results = evaluate_point_asset_exposure(
                hazard_id=hazard_id,
                hazard_polygon=hazard_polygon,
                assets=valid_assets,
            )
            for ar in asset_results:
                ar.evidence_ids.extend(hazard_eval.evidence_ids)
                exposure_results.append(ar)

        # 3. Evaluate Linear Transport Infrastructure (Roads)
        if roads:
            valid_roads = [r for r in roads if r.quality_state == QualityState.VALID]
            road_res = evaluate_road_exposure(
                hazard_id=hazard_id,
                hazard_polygon=hazard_polygon,
                roads=valid_roads,
            )
            if road_res:
                road_res.evidence_ids.extend(hazard_eval.evidence_ids)
                exposure_results.append(road_res)

        # 4. Evaluate Building Footprints
        if buildings:
            valid_blds = [b for b in buildings if b.quality_state == QualityState.VALID]
            bld_res = evaluate_building_exposure(
                hazard_id=hazard_id,
                hazard_polygon=hazard_polygon,
                buildings=valid_blds,
            )
            if bld_res:
                bld_res.evidence_ids.extend(hazard_eval.evidence_ids)
                exposure_results.append(bld_res)

        # 5. Evaluate Agricultural Land & Plots
        if agricultural_plots:
            agri_res = evaluate_agricultural_exposure(
                hazard_id=hazard_id,
                hazard_polygon=hazard_polygon,
                plots=agricultural_plots,
            )
            if agri_res:
                agri_res.evidence_ids.extend(hazard_eval.evidence_ids)
                exposure_results.append(agri_res)

        # Compute summary counts
        summary_counts: Dict[str, float] = {}
        for r in exposure_results:
            summary_counts[r.exposure_type.value] = summary_counts.get(r.exposure_type.value, 0.0) + r.quantity

        return ExposureEvaluation(
            evaluation_id=eval_id,
            hazard_evaluation_id=hazard_id,
            hazard_type=hazard_type,
            evaluated_at=datetime.now(timezone.utc),
            exposure_results=exposure_results,
            summary_counts=summary_counts,
            has_data_quality_warning=bool(quality_warnings),
            quality_warnings=quality_warnings,
        )


# Global singleton engine
exposure_engine = ExposureEngine()

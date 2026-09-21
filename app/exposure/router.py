"""FastAPI router exposing deterministic exposure evaluation endpoints.

Provides semantic/domain endpoints for exposure quantification, method introspection,
and exposure taxonomy queries.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.exposure.engine import exposure_engine
from app.exposure.method_registry import exposure_method_registry
from app.exposure.models import (
    AdministrativePopulationRecord,
    BuildingFootprint,
    CriticalAsset,
    ExposureEvaluation,
    ExposureMethodStatus,
    ExposureResult,
    ExposureType,
    GriddedPopulationCell,
    RoadSegment,
)
from app.hazard.models import HazardEvaluation, HazardState, HazardType, BasisType


exposure_router = APIRouter(prefix="/exposure", tags=["Exposure Modeling"])

# In-memory store for evaluated exposure results
_exposure_evaluation_store: Dict[str, ExposureEvaluation] = {}


class EvaluateExposureRequest(BaseModel):
    """Input payload for exposure evaluation."""
    hazard_evaluation: HazardEvaluation
    hazard_polygon: List[List[float]] = Field(
        ...,
        description="Hazard perimeter polygon coordinate ring [[lon, lat], ...]",
        min_length=3,
    )
    admin_population_records: Optional[List[Dict[str, Any]]] = None
    gridded_cells: Optional[List[Dict[str, Any]]] = None
    point_assets: Optional[List[Dict[str, Any]]] = None
    roads: Optional[List[Dict[str, Any]]] = None
    buildings: Optional[List[Dict[str, Any]]] = None
    agricultural_plots: Optional[List[Dict[str, Any]]] = None
    preferred_population_method: str = "AUTO"


@exposure_router.post("/evaluate", response_model=ExposureEvaluation)
async def evaluate_exposure(request: EvaluateExposureRequest) -> ExposureEvaluation:
    """Evaluates quantified spatial exposure across all submitted exposure layers."""
    hazard_poly = [(pt[0], pt[1]) for pt in request.hazard_polygon]

    # Parse admin records if provided
    admin_records = None
    if request.admin_population_records:
        admin_records = []
        for item in request.admin_population_records:
            rec = AdministrativePopulationRecord(**item["record"])
            poly = [(pt[0], pt[1]) for pt in item["polygon"]]
            admin_records.append((rec, poly))

    # Parse gridded cells if provided
    gridded_cells = None
    if request.gridded_cells:
        gridded_cells = [GriddedPopulationCell(**item) for item in request.gridded_cells]

    # Parse point assets if provided
    point_assets = None
    if request.point_assets:
        point_assets = [CriticalAsset(**item) for item in request.point_assets]

    # Parse roads if provided
    roads = None
    if request.roads:
        roads = [RoadSegment(**item) for item in request.roads]

    # Parse buildings if provided
    buildings = None
    if request.buildings:
        buildings = [BuildingFootprint(**item) for item in request.buildings]

    # Agricultural plots
    plots = request.agricultural_plots

    eval_result = exposure_engine.evaluate(
        hazard_eval=request.hazard_evaluation,
        hazard_polygon=hazard_poly,
        admin_population_records=admin_records,
        gridded_population_cells=gridded_cells,
        point_assets=point_assets,
        roads=roads,
        buildings=buildings,
        agricultural_plots=plots,
        preferred_population_method=request.preferred_population_method,
    )

    _exposure_evaluation_store[eval_result.evaluation_id] = eval_result
    return eval_result


@exposure_router.get("/evaluations/{evaluation_id}", response_model=ExposureEvaluation)
async def get_exposure_evaluation(evaluation_id: str) -> ExposureEvaluation:
    """Retrieves an evaluated exposure bundle by ID."""
    res = _exposure_evaluation_store.get(evaluation_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Exposure evaluation {evaluation_id} not found")
    return res


@exposure_router.get("/methods")
async def list_exposure_methods(
    exposure_type: Optional[ExposureType] = None,
    status: Optional[ExposureMethodStatus] = None,
) -> List[Dict[str, Any]]:
    """Lists registered exposure methods."""
    methods = exposure_method_registry.list_methods(exposure_type=exposure_type, status=status)
    return [m.model_dump() for m in methods]


@exposure_router.get("/methods/{method_id}")
async def get_exposure_method(method_id: str) -> Dict[str, Any]:
    """Retrieves metadata for a specific exposure quantification methodology."""
    method = exposure_method_registry.get_method(method_id)
    if not method:
        raise HTTPException(status_code=404, detail=f"Method {method_id} not found in registry")
    return method.model_dump()


@exposure_router.get("/types")
async def list_exposure_types() -> List[Dict[str, str]]:
    """Lists all supported exposure categories."""
    return [{"type": t.name, "value": t.value} for t in ExposureType]

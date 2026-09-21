"""VAYUBODHAK Phase 4 — Quantified Exposure Modeling Layer.

Deterministic, evidence-linked, spatially-grounded exposure quantification
on top of Phase 2A Evidence Foundation and Phase 3 Deterministic Hazard Modeling.
"""

from app.exposure.models import (
    ExposureType,
    SpatialResolution,
    ExposureMethodStatus,
    UncertaintyMetadata,
    CriticalAsset,
    RoadSegment,
    BuildingFootprint,
    AdministrativePopulationRecord,
    GriddedPopulationCell,
    ExposureResult,
    ExposureEvaluation,
)
from app.exposure.method_registry import ExposureMethodRegistry, exposure_method_registry
from app.exposure.engine import ExposureEngine, exposure_engine

__all__ = [
    "ExposureType",
    "SpatialResolution",
    "ExposureMethodStatus",
    "UncertaintyMetadata",
    "CriticalAsset",
    "RoadSegment",
    "BuildingFootprint",
    "AdministrativePopulationRecord",
    "GriddedPopulationCell",
    "ExposureResult",
    "ExposureEvaluation",
    "ExposureMethodRegistry",
    "exposure_method_registry",
    "ExposureEngine",
    "exposure_engine",
]

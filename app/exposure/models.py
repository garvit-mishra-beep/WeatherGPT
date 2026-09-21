"""Domain models for VAYUBODHAK Phase 4 — Quantified Exposure Modeling.

Implements canonical data contracts for population, infrastructure,
point assets, linear assets, and agricultural exposure.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.evidence.models import QualityState


# ============================================================================
# 1. Enums
# ============================================================================

class ExposureType(str, Enum):
    """Categorized human, built-environment, and natural exposure types."""
    POPULATION = "POPULATION"
    POPULATION_ADMIN = "POPULATION_ADMIN"
    POPULATION_GRIDDED = "POPULATION_GRIDDED"
    BUILDING = "BUILDING"
    ROAD = "ROAD"
    HOSPITAL = "HOSPITAL"
    SCHOOL = "SCHOOL"
    POLICE_EMERGENCY = "POLICE_EMERGENCY"
    CRITICAL_INFRASTRUCTURE = "CRITICAL_INFRASTRUCTURE"
    AGRICULTURE = "AGRICULTURE"
    ADMINISTRATIVE_ASSET = "ADMINISTRATIVE_ASSET"
    OTHER_SUPPORTED_ASSET = "OTHER_SUPPORTED_ASSET"


class SpatialResolution(str, Enum):
    """Spatial resolution or granularity of the underlying exposure dataset."""
    POINT = "POINT"
    STATION = "STATION"
    ADMINISTRATIVE_POLYGON = "ADMINISTRATIVE_POLYGON"
    BUILDING_FOOTPRINT = "BUILDING_FOOTPRINT"
    ROAD_SEGMENT = "ROAD_SEGMENT"
    POPULATION_GRID_CELL = "POPULATION_GRID_CELL"
    FORECAST_GRID = "FORECAST_GRID"
    HAZARD_POLYGON = "HAZARD_POLYGON"


class ExposureMethodStatus(str, Enum):
    """Lifecycle status for exposure quantification methodologies."""
    ACTIVE = "ACTIVE"
    DRAFT = "DRAFT"
    RETIRED = "RETIRED"


# ============================================================================
# 2. Metadata Contracts
# ============================================================================

class UncertaintyMetadata(BaseModel):
    """Methodology, assumption, and uncertainty disclosure for estimated results."""
    methodology: str = Field(..., description="Name/description of calculation method")
    spatial_resolution: SpatialResolution = Field(..., description="Granularity of input data")
    assumptions: List[str] = Field(default_factory=list, description="Methodological assumptions made")
    limitations: List[str] = Field(default_factory=list, description="Known analytical or data limitations")
    confidence_bounds: Optional[Dict[str, float]] = Field(default=None, description="Optional upper/lower bounds")
    is_estimate: bool = Field(default=True, description="True if result is an estimation rather than direct census")


# ============================================================================
# 3. Exposure Asset Models
# ============================================================================

class CriticalAsset(BaseModel):
    """Reusable asset model for critical point or localized infrastructure."""
    asset_id: str = Field(..., description="Unique asset identifier")
    asset_type: ExposureType = Field(..., description="Exposure category: HOSPITAL, SCHOOL, POLICE_EMERGENCY, etc.")
    name: str = Field(..., description="Official or operational name of asset")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Centroid latitude in EPSG:4326")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Centroid longitude in EPSG:4326")
    geometry: Optional[Dict[str, Any]] = Field(default=None, description="Optional GeoJSON geometry (Point/Polygon)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Domain attributes (e.g. bed count, station type)")
    source_id: str = Field(..., description="Registered authority source identifier")
    source_version: str = Field(default="1.0", description="Source publication version")
    quality_state: QualityState = Field(default=QualityState.VALID, description="Data validation status")


class RoadSegment(BaseModel):
    """Linear road infrastructure segment for transport network exposure."""
    road_id: str = Field(..., description="Unique road segment identifier")
    road_name: str = Field(..., description="Name or code (e.g. 'NH-48', 'SH-6')")
    road_classification: str = Field(..., description="Classification: National Highway, State Highway, etc.")
    length_km: float = Field(..., ge=0.0, description="Total length of segment in kilometers")
    coordinates: List[Tuple[float, float]] = Field(..., description="Ordered list of (longitude, latitude) coordinates")
    source_id: str = Field(..., description="Data source identifier (e.g. NHAI, OSM)")
    source_version: str = Field(default="1.0", description="Dataset version")
    quality_state: QualityState = Field(default=QualityState.VALID, description="Data validation status")


class BuildingFootprint(BaseModel):
    """Building footprint polygon for structural exposure assessment."""
    building_id: str = Field(..., description="Unique building identifier")
    building_name: Optional[str] = Field(default=None, description="Building name if designated")
    building_use: Optional[str] = Field(default="generic", description="Use type: residential, commercial, industrial")
    footprint_area_sqm: float = Field(..., ge=0.0, description="Footprint area in square meters")
    coordinates: List[List[Tuple[float, float]]] = Field(..., description="GeoJSON polygon coordinate rings [[(lon, lat)]]")
    source_id: str = Field(..., description="Data source identifier")
    source_version: str = Field(default="1.0", description="Dataset version")
    quality_state: QualityState = Field(default=QualityState.VALID, description="Data validation status")


class AdministrativePopulationRecord(BaseModel):
    """Official census or administrative population figure attached to a boundary."""
    admin_code: str = Field(..., description="Standard administrative code (e.g. 'IN-GJ-24')")
    admin_name: str = Field(..., description="Administrative name (e.g. 'Surat')")
    admin_level: str = Field(..., description="Level: state, district, subdistrict")
    total_population: int = Field(..., ge=0, description="Total enumerated population count")
    census_year: int = Field(default=2011, description="Official census enumeration year")
    total_area_sqkm: float = Field(..., gt=0.0, description="Total land area of administrative unit in sq km")
    source_id: str = Field(default="SRC-CENSUS-INDIA-2011", description="Registered authority source identifier")
    source_version: str = Field(default="2011.1", description="Census release version")
    is_historical: bool = Field(default=True, description="True since Census 2011 is historical baseline")
    quality_state: QualityState = Field(default=QualityState.VALID, description="Data quality state")


class GriddedPopulationCell(BaseModel):
    """Uniform spatial mesh/raster grid cell containing population estimates."""
    cell_id: str = Field(..., description="Unique cell identifier (e.g. 'WP-1KM-21.17-72.83')")
    centroid_lat: float = Field(..., ge=-90.0, le=90.0)
    centroid_lon: float = Field(..., ge=-180.0, le=180.0)
    resolution_meters: float = Field(default=1000.0, gt=0.0, description="Cell resolution in meters")
    population_count: float = Field(..., ge=0.0, description="Estimated population inside cell")
    bbox: Tuple[float, float, float, float] = Field(..., description="(min_lon, min_lat, max_lon, max_lat)")
    source_id: str = Field(default="SRC-WORLDPOP-GRID", description="Gridded dataset provider")
    dataset_version: str = Field(default="2020.v1", description="Dataset release version")
    quality_state: QualityState = Field(default=QualityState.VALID)


# ============================================================================
# 4. Canonical Exposure Result & Evaluation
# ============================================================================

class ExposureResult(BaseModel):
    """Canonical, structured, deterministic quantified exposure record."""
    exposure_id: str = Field(..., description="Unique deterministic exposure result ID")
    hazard_id: str = Field(..., description="Parent HazardEvaluation or HazardState ID")
    exposure_type: ExposureType = Field(..., description="Category of exposed elements")
    quantity: float = Field(..., ge=0.0, description="Quantified count, length, or area")
    unit: str = Field(..., description="Metric unit: persons, count, km, km², acres")
    location: Optional[Dict[str, Any]] = Field(default=None, description="Spatial scope or boundary identifier")
    asset_identifiers: List[str] = Field(default_factory=list, description="List of intersected asset/boundary IDs")
    source_id: str = Field(..., description="Authoritative dataset provider ID")
    source_version: str = Field(default="1.0", description="Dataset version")
    assessment_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Evaluation timestamp")
    spatial_resolution: SpatialResolution = Field(..., description="Granularity of the exposure assessment")
    quality_state: QualityState = Field(default=QualityState.VALID, description="Quality state of the result")
    uncertainty: UncertaintyMetadata = Field(..., description="Methodology, assumptions, and limitations")
    evidence_ids: List[str] = Field(default_factory=list, description="Lineage links to Phase 2A EvidenceRecords")
    provenance_id: str = Field(..., description="SHA-256 cryptographic provenance digest")
    method_id: str = Field(..., description="Registered ExposureMethod identifier")
    method_version: str = Field(default="1.0.0", description="ExposureMethod version")
    derived_from: List[str] = Field(default_factory=list, description="Parent evaluation / evidence IDs")
    intersection_area_sqkm: Optional[float] = Field(default=None, description="Geodesic intersecting area in km²")
    total_area_sqkm: Optional[float] = Field(default=None, description="Total boundary area in km²")
    overlap_fraction: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Ratio of intersection to total area")
    breakdown_details: Dict[str, Any] = Field(default_factory=dict, description="Detailed per-item or sectoral breakdown")


class ExposureEvaluation(BaseModel):
    """Complete bundle of quantified exposure assessments for a hazard event."""
    evaluation_id: str = Field(..., description="Unique evaluation bundle ID")
    hazard_evaluation_id: str = Field(..., description="Target HazardEvaluation ID")
    hazard_type: str = Field(..., description="Hazard type evaluated (e.g. HEAVY_RAINFALL, FLOOD)")
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    exposure_results: List[ExposureResult] = Field(default_factory=list)
    summary_counts: Dict[str, float] = Field(default_factory=dict, description="Summary counts keyed by exposure_type")
    has_data_quality_warning: bool = Field(default=False)
    quality_warnings: List[str] = Field(default_factory=list)

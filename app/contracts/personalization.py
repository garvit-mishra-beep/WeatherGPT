"""Optional personalization schemas across domain brains."""

from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CropContext(BaseModel):
    """Agronomic crop profile details."""
    name: str = Field(..., description="Crop name (e.g. 'Cotton', 'Wheat', 'Paddy')")
    variety: Optional[str] = Field(default=None, description="Crop variety or hybrid cultivar")
    growth_stage: Optional[str] = Field(
        default=None,
        description="Growth stage (e.g. 'vegetative', 'flowering_and_boll_formation', 'grain_filling')",
    )
    sowing_date: Optional[str] = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Date of sowing YYYY-MM-DD",
    )
    expected_harvest_date: Optional[str] = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Expected harvest date YYYY-MM-DD",
    )

    model_config = ConfigDict(frozen=True)


class FarmContext(BaseModel):
    """Field, soil, and irrigation operational metadata."""
    farm_size_acres: Optional[float] = Field(default=None, ge=0.0)
    irrigation_type: Optional[str] = Field(default=None, description="e.g. 'drip', 'sprinkler', 'flood', 'rainfed'")
    soil_type: Optional[str] = Field(
        default="medium_black_clay",
        description="Soil category (e.g. 'black_cotton_clay', 'alluvial_loam', 'red_sandy')",
    )
    soil_moisture_estimate_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    last_irrigation_date: Optional[str] = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Date of last irrigation YYYY-MM-DD",
    )
    planned_irrigation_date: Optional[str] = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Planned irrigation date YYYY-MM-DD",
    )

    model_config = ConfigDict(frozen=True)


class FarmerContextSchema(BaseModel):
    """Complete optional farmer personalization context envelope."""
    crop: Optional[CropContext] = None
    farm: Optional[FarmContext] = None

    model_config = ConfigDict(frozen=True)


class BaselinePeriod(BaseModel):
    """Climate normal baseline period range."""
    start_year: int = Field(default=1991, ge=1900, le=2100)
    end_year: int = Field(default=2020, ge=1900, le=2100)

    model_config = ConfigDict(frozen=True)


class ResearcherContextSchema(BaseModel):
    """Researcher preferences and dataset filter context."""
    preferred_datasets: List[str] = Field(
        default_factory=lambda: ["imd_gridded_0p25", "era5_reanalysis"],
        description="List of preferred meteorological datasets",
    )
    baseline_period: BaselinePeriod = Field(default_factory=BaselinePeriod)
    default_statistic: str = Field(
        default="mann_kendall_trend",
        description="Default statistical routine (e.g. 'mann_kendall_trend', 'sens_slope')",
    )
    missing_data_threshold_pct: float = Field(default=5.0, ge=0.0, le=50.0)
    export_format: str = Field(default="csv", description="'csv' or 'json'")

    model_config = ConfigDict(frozen=True)


class HazardThresholds(BaseModel):
    """Custom hazard trigger thresholds."""
    heavy_rainfall_24h_mm: float = Field(default=64.5, ge=0.0)
    very_heavy_rainfall_24h_mm: float = Field(default=115.6, ge=0.0)
    wind_gust_kmh: float = Field(default=60.0, ge=0.0)

    model_config = ConfigDict(frozen=True)


class AnalystContextSchema(BaseModel):
    """Operational risk analyst context and exposure layer preferences."""
    organization_type: str = Field(default="state_disaster_management")
    jurisdiction_admin_level: str = Field(default="district")
    target_districts: List[str] = Field(default_factory=list)
    hazard_thresholds: HazardThresholds = Field(default_factory=HazardThresholds)
    exposure_layers: List[str] = Field(
        default_factory=lambda: ["population_density", "highway_network", "power_substations"]
    )

    model_config = ConfigDict(frozen=True)


class GeneralPreferenceSchema(BaseModel):
    """Everyday user preferences."""
    preferred_units: str = Field(default="metric", description="'metric' or 'imperial'")
    saved_location_name: Optional[str] = None
    forecast_detail_level: str = Field(default="standard", description="'compact', 'standard', 'detailed'")

    model_config = ConfigDict(frozen=True)

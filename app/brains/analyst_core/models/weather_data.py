"""Meteorological domain data structures with strict lineage and QC flags."""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from app.brains.analyst_core.models.schemas import DataType, AlertSeverity, EpistemicStatus


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensures datetime is timezone-aware in UTC format."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class PhysicalLimits(BaseModel):
    """Configurable meteorological physical plausibility boundaries."""
    temp_min_c: float = -90.0
    temp_max_c: float = 60.0
    humidity_min_pct: float = 0.0
    humidity_max_pct: float = 100.0  # >100 flagged unless supersaturation allowed
    allow_supersaturation: bool = False
    wind_speed_min_kmh: float = 0.0
    wind_speed_max_kmh: float = 450.0
    rainfall_min_mm: float = 0.0
    rainfall_max_hourly_mm: float = 350.0
    pressure_min_hpa: float = 870.0
    pressure_max_hpa: float = 1085.0
    visibility_min_m: float = 0.0
    visibility_max_m: float = 100000.0


class LocationMetadata(BaseModel):
    """Geographic and station metadata."""
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    country: str = "IN"
    timezone: str = "Asia/Kolkata"
    elevation_m: Optional[float] = None
    station_id: Optional[str] = None


class WeatherObservation(BaseModel):
    """In-situ or station observation record with explicit provenance and rainfall semantics.
    
    Strictly represents physical in-situ measurements (anemometer, thermometer, AWS).
    Model-derived reanalysis or assimilation fields must use ModelAnalysis.
    """
    timestamp: datetime
    location: str
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_gust_kmh: Optional[float] = None
    rainfall_mm: Optional[float] = None
    rainfall_accumulation_period_hours: float = 1.0  # Standard 1h, 3h, or 24h accumulation
    rainfall_rate_mm_h: Optional[float] = None       # Instantaneous intensity rate
    rainfall_window_start: Optional[datetime] = None
    rainfall_window_end: Optional[datetime] = None
    pressure_hpa: Optional[float] = None
    visibility_m: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    soil_moisture_pct: Optional[float] = None
    river_level_m: Optional[float] = None
    river_discharge_m3s: Optional[float] = None     # River discharge rate in m^3/s
    data_type: DataType = DataType.OBSERVATION
    source: str = "IMD_AWS"
    producing_agency: Optional[str] = None
    data_license: Optional[str] = None
    endpoint_uri: Optional[str] = None
    retrieval_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_synthetic: bool = False
    epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED
    quality_flags: List[str] = Field(default_factory=list)
    per_variable_freshness_age_hours: Dict[str, float] = Field(default_factory=dict)
    raw_payload: Dict[str, Any] = Field(default_factory=dict)


class ModelAnalysis(BaseModel):
    """NWP analysis or reanalysis gridded assimilation field (e.g. ERA5, GFS Analysis, HRRR).
    
    Distinct from WeatherObservation: derived from numerical data assimilation models,
    not direct in-situ physical instrument sensors.
    """
    valid_time: datetime
    location: str
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_gust_kmh: Optional[float] = None
    rainfall_mm: Optional[float] = None
    rainfall_accumulation_period_hours: float = 1.0
    rainfall_rate_mm_h: Optional[float] = None
    pressure_hpa: Optional[float] = None
    soil_moisture_pct: Optional[float] = None
    model_name: str = "ECMWF-ERA5"
    reanalysis_dataset: Optional[str] = "ERA5"
    grid_resolution_km: Optional[float] = 31.0
    data_type: DataType = DataType.MODEL_ANALYSIS
    source: str = "Atmospheric Model Analysis Field"
    producing_agency: Optional[str] = None
    data_license: Optional[str] = None
    endpoint_uri: Optional[str] = None
    retrieval_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_synthetic: bool = False
    epistemic_status: EpistemicStatus = EpistemicStatus.MODEL_DERIVED
    quality_flags: List[str] = Field(default_factory=list)


class RemoteSensingObservation(BaseModel):
    """Remote sensing satellite or Doppler radar observation field.
    
    Distinct from in-situ station observations: represents area-integrated reflectance,
    cloud top temperature, or radar reflectivity (dBZ) from remote sensors.
    """
    timestamp: datetime
    location: str
    sensor_type: str = "DOPPLER_RADAR"  # "DOPPLER_RADAR", "GEO_SATELLITE", "POLAR_SATELLITE"
    band_or_channel: Optional[str] = "C-band"
    reflectivity_dbz: Optional[float] = None
    cloud_top_temp_c: Optional[float] = None
    spatial_resolution_km: Optional[float] = 1.0
    estimated_instant_rain_rate_mm_h: Optional[float] = None
    data_type: DataType = DataType.RADAR
    source: str = "IMD Doppler Weather Radar Network"
    producing_agency: Optional[str] = "India Meteorological Department"
    data_license: Optional[str] = None
    endpoint_uri: Optional[str] = None
    retrieval_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_synthetic: bool = False
    epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED
    quality_flags: List[str] = Field(default_factory=list)


class ForecastPoint(BaseModel):
    """Numerical Weather Prediction (NWP) model point forecast with verified model attribution."""
    valid_time: datetime
    location: str
    init_time: Optional[datetime] = None        # Model run initialization timestamp (None if unprovided)
    temperature_c: Optional[float] = None
    temp_min_c: Optional[float] = None
    temp_max_c: Optional[float] = None
    precipitation_prob_pct: Optional[float] = None
    rainfall_mm: Optional[float] = None
    rainfall_accumulation_period_hours: float = 1.0
    rainfall_rate_mm_h: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_gust_kmh: Optional[float] = None
    humidity_pct: Optional[float] = None
    pressure_hpa: Optional[float] = None
    cape_jkg: Optional[float] = None  # Convective Available Potential Energy
    lifted_index: Optional[float] = None
    model_name: str = "UNCONFIRMED_NWP_MODEL"  # Specific NWP model (e.g. ECMWF-IFS, NOAA-GFS)
    model_confirmed: bool = False               # Set to True ONLY when provider explicitly confirms the model variant
    model_cycle: str = "UNKNOWN_CYCLE"          # Operational NWP cycle (00Z, 06Z, 12Z, 18Z)
    lead_time_hours: Optional[float] = None     # Forecast lead time from model initialization (None if uninitialized)
    producing_center: str = "Unspecified NWP Center"
    model_version: Optional[str] = None
    forecast_step_hours: int = 1
    data_type: DataType = DataType.FORECAST_NWP
    source: str = "NWP Forecast Stream"
    data_license: Optional[str] = None
    endpoint_uri: Optional[str] = None
    retrieval_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_synthetic: bool = False
    epistemic_status: EpistemicStatus = EpistemicStatus.MODEL_DERIVED
    quality_flags: List[str] = Field(default_factory=list)


class OfficialAlert(BaseModel):
    """Verified official government / meteorological weather warning."""
    alert_id: str
    issuing_authority: str  # e.g., "India Meteorological Department (IMD)"
    warning_type: str       # e.g., "HEAVY_RAINFALL", "HEATWAVE", "CYCLONE"
    severity: AlertSeverity
    issue_time: datetime
    valid_from: datetime
    valid_to: datetime
    geographic_area: str
    headline: str
    description: str
    recommended_precautions: List[str] = Field(default_factory=list)
    bulletin_ref: Optional[str] = None
    data_license: Optional[str] = None
    endpoint_uri: Optional[str] = None
    is_verified: bool = True
    is_synthetic: bool = False
    data_type: DataType = DataType.OFFICIAL_WARNING
    epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED
    polygon_coordinates: Optional[List[Tuple[float, float]]] = None  # [(lat, lon), ...]
    affected_bounds: Optional[Tuple[float, float, float, float]] = None  # (min_lat, min_lon, max_lat, max_lon)
    storm_id: Optional[str] = None  # Official storm track/system ID (e.g. "BOB-01-2026")

    def matches_location(
        self,
        location_name: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> bool:
        """Determines if this warning applies to the given location and/or coordinates."""
        # 1. Geographic name matching
        loc_clean = location_name.strip().lower()
        area_clean = self.geographic_area.strip().lower()
        if (
            loc_clean in area_clean
            or area_clean in loc_clean
            or "all" in area_clean
            or "general" in area_clean
            or "entire" in area_clean
        ):
            return True

        # 2. Coordinate / Polygon matching
        if latitude is not None and longitude is not None:
            # Bounding box check
            if self.affected_bounds is not None:
                min_lat, min_lon, max_lat, max_lon = self.affected_bounds
                if not (min_lat <= latitude <= max_lat and min_lon <= longitude <= max_lon):
                    return False

            # Precise point-in-polygon check (Ray casting algorithm)
            if self.polygon_coordinates and len(self.polygon_coordinates) >= 3:
                inside = False
                n = len(self.polygon_coordinates)
                p1_lat, p1_lon = self.polygon_coordinates[0]
                for i in range(1, n + 1):
                    p2_lat, p2_lon = self.polygon_coordinates[i % n]
                    if min(p1_lon, p2_lon) < longitude <= max(p1_lon, p2_lon):
                        if latitude <= max(p1_lat, p2_lat):
                            if p1_lon != p2_lon:
                                xinters = (longitude - p1_lon) * (p2_lat - p1_lat) / (p2_lon - p1_lon) + p1_lat
                                if p1_lat == p2_lat or latitude <= xinters:
                                    inside = not inside
                    p1_lat, p1_lon = p2_lat, p2_lon
                return inside

        return False


class ModelEnsemble(BaseModel):
    """Multi-model ensemble comparison and spread metrics."""
    models: List[str]
    forecasts_by_model: Dict[str, List[ForecastPoint]]
    mean_temp_c: Optional[float] = None
    temp_spread_c: Optional[float] = None
    mean_rainfall_mm: Optional[float] = None
    rainfall_spread_mm: Optional[float] = None
    agreement_score: float = 1.0  # 0.0 (high disagreement) to 1.0 (perfect agreement)
    agreement_summary: str = "High model agreement"

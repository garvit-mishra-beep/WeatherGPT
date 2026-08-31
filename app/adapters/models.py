"""Normalized Meteorological Data Contracts for WeatherGPT Adapters."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import WarningLevel


class ProviderQuality(str, Enum):
    """Data quality and freshness indicator."""
    VALID = "VALID"
    PARTIAL = "PARTIAL"
    STALE = "STALE"
    INVALID = "INVALID"
    UNAVAILABLE = "UNAVAILABLE"


class ProviderAuthority(str, Enum):
    """Authority and trust classification."""
    OFFICIAL = "OFFICIAL"               # e.g. IMD official alerts & bulletins
    NUMERICAL_MODEL = "NUMERICAL_MODEL" # e.g. GFS 0.25° physics forecast
    SECONDARY = "SECONDARY"             # e.g. Open-Meteo operational blend
    FALLBACK = "FALLBACK"               # Secondary proxy used in absence of primary


# ============================================================================
# 1. Surface Weather Observations
# ============================================================================

class NormalizedWeatherObservation(BaseModel):
    """Normalized surface meteorological observation for a coordinate."""
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    elevation_m: Optional[float] = None
    observation_time_iso: str = Field(description="ISO 8601 observation timestamp")

    # Thermal
    temperature_c: float = Field(ge=-50.0, le=60.0)
    feels_like_c: Optional[float] = Field(default=None, ge=-50.0, le=70.0)
    temperature_max_c: Optional[float] = None
    temperature_min_c: Optional[float] = None

    # Moisture & Precipitation
    relative_humidity_pct: float = Field(ge=0.0, le=100.0)
    dew_point_c: Optional[float] = None
    precipitation_mm: float = Field(default=0.0, ge=0.0)
    precipitation_last_1h_mm: Optional[float] = Field(default=None, ge=0.0)
    precipitation_last_24h_mm: Optional[float] = Field(default=None, ge=0.0)
    rain_intensity_category: str = Field(default="no_rain", description="IMD rain intensity standard")

    # Wind & Dynamics
    wind_speed_kmh: float = Field(ge=0.0, le=350.0)
    wind_speed_ms: Optional[float] = Field(default=None, ge=0.0)
    wind_gust_kmh: Optional[float] = Field(default=None, ge=0.0)
    wind_direction_deg: Optional[float] = Field(default=None, ge=0.0, le=360.0)
    surface_pressure_hpa: Optional[float] = Field(default=None, ge=700.0, le=1100.0)

    # Atmosphere & Sky
    solar_radiation_w_m2: Optional[float] = Field(default=None, ge=0.0)
    cloud_cover_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    weather_condition: str = Field(default="clear")

    # Metadata & Provenance
    station_id: Optional[str] = None
    station_name: Optional[str] = None
    provider: str = Field(description="Originating provider (e.g. 'IMD', 'Open-Meteo')")
    data_source: str = Field(description="Specific feed or API endpoint")
    authority: ProviderAuthority = Field(default=ProviderAuthority.SECONDARY)
    quality: ProviderQuality = Field(default=ProviderQuality.VALID)
    retrieval_timestamp_iso: str = Field(description="ISO 8601 timestamp when fetched")

    model_config = ConfigDict(frozen=True)


# ============================================================================
# 2. Weather Forecast (Hourly & Daily)
# ============================================================================

class NormalizedHourlyForecastPoint(BaseModel):
    """Normalized single-hour weather forecast point."""
    time_iso: str = Field(description="Forecast validity ISO 8601 timestamp")
    temperature_c: float
    feels_like_c: Optional[float] = None
    relative_humidity_pct: float = Field(ge=0.0, le=100.0)
    precipitation_mm: float = Field(default=0.0, ge=0.0)
    rain_probability_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    wind_speed_kmh: float = Field(default=0.0, ge=0.0)
    wind_direction_deg: Optional[float] = Field(default=None, ge=0.0, le=360.0)
    wind_gust_kmh: Optional[float] = Field(default=None, ge=0.0)
    surface_pressure_hpa: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    weather_condition: str = Field(default="clear")

    model_config = ConfigDict(frozen=True)


class NormalizedDailyForecastPoint(BaseModel):
    """Normalized single-day aggregated weather forecast point."""
    date_str: str = Field(description="Date in YYYY-MM-DD format")
    temp_max_c: float
    temp_min_c: float
    precipitation_sum_mm: float = Field(default=0.0, ge=0.0)
    precipitation_probability_max_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    rain_intensity_category: str = Field(default="no_rain")
    wind_speed_max_kmh: float = Field(default=0.0, ge=0.0)
    wind_direction_dominant_deg: Optional[float] = None
    weather_condition: str = Field(default="clear")

    model_config = ConfigDict(frozen=True)


class NormalizedWeatherForecastPayload(BaseModel):
    """Complete multi-day / hourly forecast package."""
    latitude: float
    longitude: float
    forecast_start_iso: str
    forecast_end_iso: str
    hourly: List[NormalizedHourlyForecastPoint] = Field(default_factory=list)
    daily: List[NormalizedDailyForecastPoint] = Field(default_factory=list)

    # Provenance
    provider: str
    model_name: Optional[str] = None
    model_run_cycle: Optional[str] = None
    authority: ProviderAuthority = Field(default=ProviderAuthority.SECONDARY)
    quality: ProviderQuality = Field(default=ProviderQuality.VALID)
    retrieval_timestamp_iso: str

    model_config = ConfigDict(frozen=True)


# ============================================================================
# 3. Official Severe Weather Warnings (IMD / CAP)
# ============================================================================

class NormalizedOfficialAlert(BaseModel):
    """Authoritative official warning item (OASIS CAP / IMD standard)."""
    alert_id: str = Field(description="Unique alert identifier")
    sender: str = Field(description="Agency sending the alert (e.g. IMD, NDMA)")
    sent_time_iso: str
    status: str = Field(default="Actual", description="Actual, Exercise, Test")
    message_type: str = Field(default="Alert", description="Alert, Update, Cancel")

    # Severity & Classification (Severity is IMMUTABLE)
    warning_level: WarningLevel = Field(description="Green, Yellow, Orange, Red")
    event_title: str = Field(description="Hazard event name (e.g. 'Heavy Rain', 'Thunderstorm')")
    urgency: str = Field(default="Immediate", description="Immediate, Expected, Future")
    severity: str = Field(default="Severe", description="Extreme, Severe, Moderate, Minor")
    certainty: str = Field(default="Observed", description="Observed, Likely, Possible")

    # Text Bulletins
    headline: Optional[str] = None
    description: str
    instruction: Optional[str] = None

    # Temporal Validity Window
    effective_time_iso: Optional[str] = None
    onset_time_iso: Optional[str] = None
    expires_time_iso: str

    # Spatial Scope
    area_description: str
    polygons: List[str] = Field(default_factory=list, description="Coordinate polygon strings if provided")
    geocodes: List[Dict[str, str]] = Field(default_factory=list, description="State/district P-codes or geocodes")

    # Authority & Provenance
    issuing_office: Optional[str] = None
    is_official: bool = Field(default=True, description="True for verified official IMD alerts")
    quality: ProviderQuality = Field(default=ProviderQuality.VALID)

    model_config = ConfigDict(frozen=True)


# ============================================================================
# 4. Numerical Weather Prediction (NWP) Grids (GFS 0.25°)
# ============================================================================

class NormalizedNWPGridPoint(BaseModel):
    """Extracted physical prognostic atmospheric field at a coordinate grid point."""
    latitude: float
    longitude: float
    model_name: str = Field(default="GFS_0P25")
    initialization_time_iso: str = Field(description="Model run initialization cycle (00z, 06z, 12z, 18z)")
    forecast_lead_hours: int = Field(ge=0, description="Hours after initialization")
    valid_time_iso: str = Field(description="Target valid forecast time")

    # Physical Surface Parameters
    temperature_2m_c: float
    relative_humidity_2m_pct: float = Field(ge=0.0, le=100.0)
    accumulated_precip_mm: float = Field(ge=0.0)
    step_precip_mm: float = Field(ge=0.0)
    u_wind_10m_ms: float
    v_wind_10m_ms: float
    wind_speed_kmh: float = Field(ge=0.0)
    wind_direction_deg: float = Field(ge=0.0, le=360.0)
    wind_gust_kmh: Optional[float] = Field(default=None, ge=0.0)
    pressure_msl_hpa: float
    total_cloud_cover_pct: float = Field(ge=0.0, le=100.0)
    cape_jkg: Optional[float] = Field(default=None, ge=0.0, description="Convective Available Potential Energy (J/kg)")

    # Grid Specs & Status
    grid_resolution_deg: float = Field(default=0.25)
    provider: str = Field(default="NOAA / NCEP")
    quality: ProviderQuality = Field(default=ProviderQuality.VALID)
    status_message: Optional[str] = Field(default=None, description="Detailed availability or data stream status message")

    model_config = ConfigDict(frozen=True)


# ============================================================================
# 5. Environmental & Air Quality Measurements (OpenAQ)
# ============================================================================

class NormalizedAirQualityMeasurement(BaseModel):
    """Normalized environmental air quality observation for a location."""
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    location_name: Optional[str] = None
    city: Optional[str] = None
    country: str = Field(default="IN")
    observation_time_iso: str = Field(description="ISO 8601 observation timestamp")

    # Pollutant concentrations (in standard units: µg/m³ or ppm)
    pm25_ug_m3: Optional[float] = Field(default=None, ge=0.0, description="Particulate Matter <2.5µm (µg/m³)")
    pm10_ug_m3: Optional[float] = Field(default=None, ge=0.0, description="Particulate Matter <10µm (µg/m³)")
    o3_ug_m3: Optional[float] = Field(default=None, ge=0.0, description="Ozone O3 (µg/m³)")
    no2_ug_m3: Optional[float] = Field(default=None, ge=0.0, description="Nitrogen Dioxide NO2 (µg/m³)")
    so2_ug_m3: Optional[float] = Field(default=None, ge=0.0, description="Sulfur Dioxide SO2 (µg/m³)")
    co_ug_m3: Optional[float] = Field(default=None, ge=0.0, description="Carbon Monoxide CO (µg/m³)")
    aqi_calculated: Optional[int] = Field(default=None, ge=0, le=500, description="Estimated/reported Air Quality Index")

    # Provenance & Source Metadata
    station_id: Optional[str] = None
    provider: str = Field(default="openaq", description="Originating provider (e.g. 'openaq')")
    data_source: str = Field(default="OpenAQ API", description="Underlying sensor or reporting network")
    authority: ProviderAuthority = Field(default=ProviderAuthority.SECONDARY)
    quality: ProviderQuality = Field(default=ProviderQuality.VALID)
    retrieval_timestamp_iso: str = Field(description="ISO 8601 timestamp when fetched")

    model_config = ConfigDict(frozen=True)

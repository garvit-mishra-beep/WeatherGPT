"""GFS 0.25° Numerical Weather Prediction Data Models."""

from typing import Dict, Optional
from pydantic import BaseModel, Field


class GFSAtmosphericParameters(BaseModel):
    """Raw atmospheric variables from GFS 0.25° NWP model."""
    tmp_2m_k: float = Field(description="2m Air Temperature in Kelvin")
    rh_2m_pct: float = Field(ge=0.0, le=100.0, description="2m Relative Humidity (%)")
    apcp_surface_kg_m2: float = Field(ge=0.0, description="Accumulated Surface Precipitation (mm / kg/m²)")
    ugrd_10m_ms: float = Field(description="10m U-Wind component (m/s)")
    vgrd_10m_ms: float = Field(description="10m V-Wind component (m/s)")
    gust_surface_ms: Optional[float] = Field(default=None, ge=0.0, description="Surface wind gust (m/s)")
    prmsl_pa: float = Field(description="Pressure reduced to MSL in Pascals")
    tcdc_pct: float = Field(ge=0.0, le=100.0, description="Total cloud cover fraction (%)")


class GFSGridMessage(BaseModel):
    """Container for GFS grid message metadata and physical fields."""
    cycle_time_iso: str
    forecast_hour: int = Field(ge=0)
    valid_time_iso: str
    latitude: float
    longitude: float
    variables: GFSAtmosphericParameters

"""Location schemas and coordinate validation."""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.contracts.enums import LocationSource

# Indian subcontinent geographical bounding box
MIN_LATITUDE = 6.0
MAX_LATITUDE = 38.0
MIN_LONGITUDE = 68.0
MAX_LONGITUDE = 98.0


class Coordinates(BaseModel):
    """Geographic point coordinates in WGS 84 (EPSG:4326)."""
    latitude: float = Field(
        ...,
        description="Latitude in decimal degrees (Indian BBox: 6.0 to 38.0)",
        ge=-90.0,
        le=90.0,
    )
    longitude: float = Field(
        ...,
        description="Longitude in decimal degrees (Indian BBox: 68.0 to 98.0)",
        ge=-180.0,
        le=180.0,
    )

    model_config = ConfigDict(frozen=True)

    @field_validator("latitude")
    @classmethod
    def validate_indian_latitude(cls, v: float) -> float:
        if not (MIN_LATITUDE <= v <= MAX_LATITUDE):
            raise ValueError(
                f"Latitude {v} is outside the supported Indian subcontinent bounding box ({MIN_LATITUDE}°N to {MAX_LATITUDE}°N)"
            )
        return round(v, 5)

    @field_validator("longitude")
    @classmethod
    def validate_indian_longitude(cls, v: float) -> float:
        if not (MIN_LONGITUDE <= v <= MAX_LONGITUDE):
            raise ValueError(
                f"Longitude {v} is outside the supported Indian subcontinent bounding box ({MIN_LONGITUDE}°E to {MAX_LONGITUDE}°E)"
            )
        return round(v, 5)


class GPSLocation(BaseModel):
    """Raw GPS coordinate reading from a mobile device."""
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    accuracy_meters: Optional[float] = Field(default=None, ge=0.0)

    model_config = ConfigDict(frozen=True)


class LocationContext(BaseModel):
    """Resolved and normalized geographic context."""
    source: LocationSource = Field(default=LocationSource.USER_QUERY)
    name: str = Field(..., min_length=1, description="Primary resolved place name or city")
    district: Optional[str] = Field(default=None, description="Admin Level 2 District name")
    state: Optional[str] = Field(default=None, description="Admin Level 1 State/UT name")
    country: str = Field(default="India")
    latitude: float = Field(..., ge=MIN_LATITUDE, le=MAX_LATITUDE)
    longitude: float = Field(..., ge=MIN_LONGITUDE, le=MAX_LONGITUDE)
    elevation_m: Optional[float] = Field(default=None, description="Elevation above sea level in meters")
    admin_pcode: Optional[str] = Field(default=None, description="Standardized administrative P-code (e.g. IN-GJ-24)")

    model_config = ConfigDict(frozen=True)

    @property
    def coordinates(self) -> Coordinates:
        """Helper returning validated Coordinates instance."""
        return Coordinates(latitude=self.latitude, longitude=self.longitude)

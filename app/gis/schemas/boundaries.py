"""Pydantic v2 schemas for administrative boundaries and spatial resolutions."""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class AdminLevel(str, Enum):
    """Supported administrative levels in the hierarchy."""
    COUNTRY = "country"
    STATE = "state"
    DISTRICT = "district"
    SUBDISTRICT = "subdistrict"


class BoundarySummary(BaseModel):
    """Lightweight summary of an administrative boundary entity."""
    code: str = Field(description="Unique official administrative code")
    name: str = Field(description="Official administrative name")
    level: AdminLevel = Field(description="Administrative hierarchy level")
    parent_code: Optional[str] = Field(default=None, description="Parent administrative code")
    area_sqkm: Optional[float] = Field(default=None, description="Area in sq km")
    centroid_lat: Optional[float] = Field(default=None, description="Centroid latitude (WGS84)")
    centroid_lon: Optional[float] = Field(default=None, description="Centroid longitude (WGS84)")


class HierarchyResolutionResult(BaseModel):
    """Result of reverse-geocoding coordinates to administrative hierarchy."""
    latitude: float = Field(description="Queried latitude")
    longitude: float = Field(description="Queried longitude")
    country: Optional[BoundarySummary] = Field(default=None, description="Enclosing country")
    state: Optional[BoundarySummary] = Field(default=None, description="Enclosing state / UT")
    district: Optional[BoundarySummary] = Field(default=None, description="Enclosing district")
    subdistrict: Optional[BoundarySummary] = Field(default=None, description="Enclosing subdistrict / tehsil")
    resolved: bool = Field(description="True if at least state and district were resolved")


class IngestionRecordResult(BaseModel):
    """Status of a single feature ingestion."""
    code: str
    status: Literal["inserted", "updated", "skipped", "error"]
    message: Optional[str] = None


class IngestionSummary(BaseModel):
    """Summary of a GeoJSON ingestion job."""
    level: AdminLevel
    total_features: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    errors: List[str] = Field(default_factory=list)

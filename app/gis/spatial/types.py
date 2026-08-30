"""Pydantic v2 typed inputs, outputs, and contracts for the Spatial Engine."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

from app.gis.schemas.boundaries import AdminLevel


# ============================================================================
# 1. Spatial Inputs
# ============================================================================

class SpatialPointInput(BaseModel):
    """Input geographic coordinate point in WGS84 (EPSG:4326)."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees (-90 to 90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees (-180 to 180)")


class BoundingBoxInput(BaseModel):
    """Geographic bounding box defined by minimum and maximum coordinates in EPSG:4326."""
    min_lat: float = Field(..., ge=-90.0, le=90.0, description="Minimum latitude (South)")
    min_lon: float = Field(..., ge=-180.0, le=180.0, description="Minimum longitude (West)")
    max_lat: float = Field(..., ge=-90.0, le=90.0, description="Maximum latitude (North)")
    max_lon: float = Field(..., ge=-180.0, le=180.0, description="Maximum longitude (East)")

    @field_validator("max_lat")
    @classmethod
    def validate_latitude_order(cls, v: float, info) -> float:
        min_lat = info.data.get("min_lat")
        if min_lat is not None and v < min_lat:
            raise ValueError(f"max_lat ({v}) must be greater than or equal to min_lat ({min_lat})")
        return v

    @field_validator("max_lon")
    @classmethod
    def validate_longitude_order(cls, v: float, info) -> float:
        min_lon = info.data.get("min_lon")
        if min_lon is not None and v < min_lon:
            raise ValueError(f"max_lon ({v}) must be greater than or equal to min_lon ({min_lon})")
        return v


class GeoJSONGeometryInput(BaseModel):
    """Standard RFC 7946 GeoJSON Geometry object in WGS84 (EPSG:4326)."""
    type: Literal["Point", "Polygon", "MultiPolygon"] = Field(..., description="GeoJSON geometry type")
    coordinates: List[Any] = Field(..., description="GeoJSON coordinates array with [lon, lat] ordering")


# ============================================================================
# 2. Spatial Results & Output Contracts
# ============================================================================

class BoundaryMatch(BaseModel):
    """Standardized metadata for a resolved administrative boundary."""
    code: str = Field(..., description="Official administrative code (e.g. 'IN', 'IN-GJ', 'GJ-SURAT')")
    name: str = Field(..., description="Administrative name (e.g. 'Gujarat', 'Surat')")
    level: AdminLevel = Field(..., description="Administrative level (country, state, district, subdistrict)")
    parent_code: Optional[str] = Field(default=None, description="Parent administrative unit code")
    area_sqkm: Optional[float] = Field(default=None, description="Land area in square kilometers")
    centroid_lat: Optional[float] = Field(default=None, description="Centroid latitude (WGS84)")
    centroid_lon: Optional[float] = Field(default=None, description="Centroid longitude (WGS84)")


class PointContainmentResult(BaseModel):
    """Hierarchical point-in-polygon resolution result across administrative tiers."""
    latitude: float
    longitude: float
    country: Optional[BoundaryMatch] = None
    state: Optional[BoundaryMatch] = None
    district: Optional[BoundaryMatch] = None
    subdistrict: Optional[BoundaryMatch] = None
    is_resolved: bool = Field(description="True if both state and district levels were resolved")


class IntersectionMatch(BaseModel):
    """Individual boundary unit overlapping an input geometry."""
    boundary: BoundaryMatch
    exposed_area_sqkm: float = Field(ge=0.0, description="Geodesic overlapping area in square kilometers")
    exposed_area_pct: float = Field(ge=0.0, le=100.0, description="Percentage of the administrative boundary overlapping")
    intersection_geojson: Optional[Dict[str, Any]] = Field(default=None, description="Clipped intersection geometry GeoJSON")


class IntersectionResult(BaseModel):
    """Aggregate result of a polygon / multipolygon spatial intersection query."""
    geometry_type: str
    target_level: AdminLevel
    total_intersections: int
    matches: List[IntersectionMatch]


class ProximityMatch(BaseModel):
    """Administrative feature with geodesic distance from an origin point."""
    boundary: BoundaryMatch
    distance_meters: float = Field(ge=0.0, description="Geodesic distance to boundary in meters")


class ProximityResult(BaseModel):
    """Result of a nearest-neighbor / proximity query around a coordinate point."""
    origin_latitude: float
    origin_longitude: float
    max_distance_meters: float
    total_matches: int
    matches: List[ProximityMatch]


class BBoxQueryResult(BaseModel):
    """Result of a bounding-box spatial envelope query."""
    bbox: BoundingBoxInput
    target_level: AdminLevel
    total_matches: int
    matches: List[BoundaryMatch]

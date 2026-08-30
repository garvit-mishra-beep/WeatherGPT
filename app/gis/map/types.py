"""Pydantic v2 typed contracts for Map-Ready Data and Declarative Map Specifications."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GeoJSONGeometryType(str, Enum):
    """Standard OGC / RFC 7946 GeoJSON geometry types."""
    POINT = "Point"
    MULTI_POINT = "MultiPoint"
    LINE_STRING = "LineString"
    MULTI_LINE_STRING = "MultiLineString"
    POLYGON = "Polygon"
    MULTI_POLYGON = "MultiPolygon"
    GEOMETRY_COLLECTION = "GeometryCollection"


class GeoJSONFeature(BaseModel):
    """Standard RFC 7946 GeoJSON Feature with deterministic ID."""
    type: str = Field(default="Feature")
    id: Optional[str] = None
    geometry: Dict[str, Any]
    properties: Dict[str, Any] = Field(default_factory=dict)


class GeoJSONFeatureCollection(BaseModel):
    """Standard RFC 7946 GeoJSON FeatureCollection."""
    type: str = Field(default="FeatureCollection")
    features: List[GeoJSONFeature] = Field(default_factory=list)
    bbox: Optional[List[float]] = Field(default=None, description="[min_lon, min_lat, max_lon, max_lat]")
    metadata: Optional[Dict[str, Any]] = None


class MapLayerType(str, Enum):
    """MapLibre GL / Leaflet layer rendering types."""
    FILL = "fill"
    LINE = "line"
    CIRCLE = "circle"
    SYMBOL = "symbol"
    RASTER = "raster"


class MapLayerSpec(BaseModel):
    """Declarative MapLibre GL compatible vector layer specification."""
    id: str
    name: str
    type: MapLayerType
    source_id: str
    source_type: str = "geojson"
    source_data: Optional[GeoJSONFeatureCollection] = None
    paint: Dict[str, Any] = Field(default_factory=dict)
    layout: Optional[Dict[str, Any]] = None
    min_zoom: Optional[float] = None
    max_zoom: Optional[float] = None
    visible: bool = True


class MapLegendItem(BaseModel):
    """Standardized legend entry."""
    label: str
    color: str
    value_range: Optional[str] = None
    hazard_type: Optional[str] = None
    official_level: Optional[str] = None


class MapViewport(BaseModel):
    """Declarative camera viewport centered on geometry."""
    center: List[float] = Field(description="[longitude, latitude] in EPSG:4326")
    zoom: float = Field(default=8.5, ge=0.0, le=24.0)
    pitch: float = Field(default=0.0, ge=0.0, le=85.0)
    bearing: float = Field(default=0.0, ge=-180.0, le=180.0)
    bbox: Optional[List[float]] = Field(default=None, description="[min_lon, min_lat, max_lon, max_lat]")


class MapSpecification(BaseModel):
    """Declarative Map Specification contract for client map rendering."""
    type: str = Field(default="map_specification")
    id: str
    title: str
    viewport: MapViewport
    layers: List[MapLayerSpec] = Field(default_factory=list)
    legend: List[MapLegendItem] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    quality: str = "AVAILABLE"

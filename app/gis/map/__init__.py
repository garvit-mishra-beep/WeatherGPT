r"""WeatherGPT Map-Ready Data Package.

Converts spatial, meteorological, NWP, and GIS analytical outputs into
declarative, frontend-independent, mobile-friendly Map Specifications:
- Valid standard GeoJSON ([longitude, latitude] in EPSG:4326)
- Declarative MapLibre GL & Leaflet layer specifications
- Viewport and bounding box calculations
- Douglas-Peucker mobile geometry simplification
- Deterministic canonical JSON serialization
"""

from app.gis.map.builder import MapDataBuilder
from app.gis.map.errors import (
    InvalidCoordinatesError,
    InvalidGeoJSONError,
    MapDataError,
    MapLayerBuildError,
    ViewportCalculationError,
)
from app.gis.map.geojson import (
    create_feature_collection,
    create_multipolygon_feature,
    create_point_feature,
    create_polygon_feature,
    extract_geometry_bbox,
    validate_coordinates,
)
from app.gis.map.legend import (
    build_risk_legend,
    build_warning_legend,
    build_weather_legend,
)
from app.gis.map.serializer import serialize_map_data
from app.gis.map.simplification import (
    simplify_feature,
    simplify_feature_collection,
    simplify_geometry,
    simplify_ring,
)
from app.gis.map.styling import (
    get_administrative_boundary_paint,
    get_analytical_risk_paint,
    get_official_warning_paint,
    get_weather_point_paint,
)
from app.gis.map.types import (
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    GeoJSONGeometryType,
    MapLayerSpec,
    MapLayerType,
    MapLegendItem,
    MapSpecification,
    MapViewport,
)
from app.gis.map.viewport import calculate_bounds, calculate_viewport

__all__ = [
    # Builder
    "MapDataBuilder",
    # Functions
    "create_point_feature",
    "create_polygon_feature",
    "create_multipolygon_feature",
    "create_feature_collection",
    "extract_geometry_bbox",
    "validate_coordinates",
    "calculate_bounds",
    "calculate_viewport",
    "get_official_warning_paint",
    "get_analytical_risk_paint",
    "get_administrative_boundary_paint",
    "get_weather_point_paint",
    "build_warning_legend",
    "build_risk_legend",
    "build_weather_legend",
    "simplify_ring",
    "simplify_geometry",
    "simplify_feature",
    "simplify_feature_collection",
    "serialize_map_data",
    # Types
    "GeoJSONGeometryType",
    "GeoJSONFeature",
    "GeoJSONFeatureCollection",
    "MapLayerType",
    "MapLayerSpec",
    "MapLegendItem",
    "MapViewport",
    "MapSpecification",
    # Errors
    "MapDataError",
    "InvalidCoordinatesError",
    "InvalidGeoJSONError",
    "MapLayerBuildError",
    "ViewportCalculationError",
]

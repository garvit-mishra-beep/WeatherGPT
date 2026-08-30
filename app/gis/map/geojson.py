"""Standard RFC 7946 GeoJSON Builders & Coordinate Order Enforcers.

CRITICAL INVARIANT:
GeoJSON coordinates are strictly [longitude, latitude] in EPSG:4326.
"""

from typing import Any, Dict, List, Optional, Tuple, Union

from app.gis.map.errors import InvalidCoordinatesError, InvalidGeoJSONError
from app.gis.map.types import GeoJSONFeature, GeoJSONFeatureCollection


def validate_coordinates(longitude: float, latitude: float) -> None:
    """Validates that longitude and latitude lie within valid WGS84 EPSG:4326 bounds."""
    if not (-180.0 <= longitude <= 180.0):
        raise InvalidCoordinatesError(
            f"Longitude ({longitude}) must be in range [-180.0, 180.0]. Check coordinate ordering [lon, lat]."
        )
    if not (-90.0 <= latitude <= 90.0):
        raise InvalidCoordinatesError(
            f"Latitude ({latitude}) must be in range [-90.0, 90.0]. Check coordinate ordering [lon, lat]."
        )


def create_point_feature(
    latitude: float,
    longitude: float,
    properties: Optional[Dict[str, Any]] = None,
    feature_id: Optional[str] = None,
) -> GeoJSONFeature:
    """Constructs a standard GeoJSON Point feature with strict [lon, lat] coordinate ordering."""
    validate_coordinates(longitude=longitude, latitude=latitude)

    return GeoJSONFeature(
        id=feature_id,
        geometry={
            "type": "Point",
            "coordinates": [round(longitude, 6), round(latitude, 6)],
        },
        properties=properties or {},
    )


def create_polygon_feature(
    coordinates: List[List[List[float]]],
    properties: Optional[Dict[str, Any]] = None,
    feature_id: Optional[str] = None,
) -> GeoJSONFeature:
    """Constructs a standard GeoJSON Polygon feature with verified closed rings and [lon, lat] ordering."""
    if not coordinates or not coordinates[0]:
        raise InvalidGeoJSONError("Polygon must contain at least one linear ring")

    for ring in coordinates:
        if len(ring) < 4:
            raise InvalidGeoJSONError(f"Linear ring must contain at least 4 coordinates (found {len(ring)})")
        # Validate closure
        if ring[0] != ring[-1]:
            # Close ring automatically if endpoints match within floating tolerance or append start
            if abs(ring[0][0] - ring[-1][0]) < 1e-7 and abs(ring[0][1] - ring[-1][1]) < 1e-7:
                ring[-1] = ring[0]
            else:
                ring.append(ring[0])
        for pt in ring:
            validate_coordinates(longitude=pt[0], latitude=pt[1])

    return GeoJSONFeature(
        id=feature_id,
        geometry={
            "type": "Polygon",
            "coordinates": coordinates,
        },
        properties=properties or {},
    )


def create_multipolygon_feature(
    coordinates: List[List[List[List[float]]]],
    properties: Optional[Dict[str, Any]] = None,
    feature_id: Optional[str] = None,
) -> GeoJSONFeature:
    """Constructs a standard GeoJSON MultiPolygon feature."""
    if not coordinates:
        raise InvalidGeoJSONError("MultiPolygon coordinates list cannot be empty")

    for poly in coordinates:
        for ring in poly:
            if len(ring) < 4:
                raise InvalidGeoJSONError(f"Linear ring must contain at least 4 coordinates (found {len(ring)})")
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            for pt in ring:
                validate_coordinates(longitude=pt[0], latitude=pt[1])

    return GeoJSONFeature(
        id=feature_id,
        geometry={
            "type": "MultiPolygon",
            "coordinates": coordinates,
        },
        properties=properties or {},
    )


def extract_geometry_bbox(geometry: Dict[str, Any]) -> List[float]:
    """Calculates [min_lon, min_lat, max_lon, max_lat] from a standard GeoJSON geometry."""
    g_type = geometry.get("type")
    coords = geometry.get("coordinates", [])

    min_lon, min_lat = 180.0, 90.0
    max_lon, max_lat = -180.0, -90.0

    def update_bounds(pt: List[float]) -> None:
        nonlocal min_lon, min_lat, max_lon, max_lat
        lon, lat = pt[0], pt[1]
        min_lon = min(min_lon, lon)
        min_lat = min(min_lat, lat)
        max_lon = max(max_lon, lon)
        max_lat = max(max_lat, lat)

    if g_type == "Point":
        update_bounds(coords)
    elif g_type in ("MultiPoint", "LineString"):
        for pt in coords:
            update_bounds(pt)
    elif g_type in ("MultiLineString", "Polygon"):
        for ring in coords:
            for pt in ring:
                update_bounds(pt)
    elif g_type == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                for pt in ring:
                    update_bounds(pt)

    if min_lon > max_lon:
        return [0.0, 0.0, 0.0, 0.0]

    return [round(min_lon, 6), round(min_lat, 6), round(max_lon, 6), round(max_lat, 6)]


def create_feature_collection(
    features: List[GeoJSONFeature],
    metadata: Optional[Dict[str, Any]] = None,
    compute_bbox: bool = True,
) -> GeoJSONFeatureCollection:
    """Constructs a standard RFC 7946 GeoJSON FeatureCollection with optional overall bounding box."""
    bbox = None
    if compute_bbox and features:
        min_lon, min_lat = 180.0, 90.0
        max_lon, max_lat = -180.0, -90.0
        for feat in features:
            f_bbox = extract_geometry_bbox(feat.geometry)
            if f_bbox != [0.0, 0.0, 0.0, 0.0]:
                min_lon = min(min_lon, f_bbox[0])
                min_lat = min(min_lat, f_bbox[1])
                max_lon = max(max_lon, f_bbox[2])
                max_lat = max(max_lat, f_bbox[3])
        if min_lon <= max_lon:
            bbox = [round(min_lon, 6), round(min_lat, 6), round(max_lon, 6), round(max_lat, 6)]

    return GeoJSONFeatureCollection(
        type="FeatureCollection",
        features=features,
        bbox=bbox,
        metadata=metadata,
    )

"""Deterministic Viewport & Bounding Box Calculation Engine."""

from typing import Any, Dict, List, Optional, Union

from app.gis.map.errors import ViewportCalculationError
from app.gis.map.geojson import extract_geometry_bbox
from app.gis.map.types import GeoJSONFeature, GeoJSONFeatureCollection, MapViewport


def calculate_bounds(
    target: Union[Dict[str, Any], GeoJSONFeature, GeoJSONFeatureCollection, List[float]]
) -> List[float]:
    """Calculates [min_lon, min_lat, max_lon, max_lat] in EPSG:4326."""
    if isinstance(target, list) and len(target) == 4:
        return [round(float(v), 6) for v in target]

    if isinstance(target, GeoJSONFeatureCollection):
        if target.bbox:
            return target.bbox
        if not target.features:
            return [68.0, 6.0, 98.0, 38.0]  # India BBox default fallback
        min_lon, min_lat = 180.0, 90.0
        max_lon, max_lat = -180.0, -90.0
        for feat in target.features:
            b = extract_geometry_bbox(feat.geometry)
            if b != [0.0, 0.0, 0.0, 0.0]:
                min_lon, min_lat = min(min_lon, b[0]), min(min_lat, b[1])
                max_lon, max_lat = max(max_lon, b[2]), max(max_lat, b[3])
        return [round(min_lon, 6), round(min_lat, 6), round(max_lon, 6), round(max_lat, 6)]

    if isinstance(target, GeoJSONFeature):
        return extract_geometry_bbox(target.geometry)

    if isinstance(target, dict):
        if target.get("type") == "FeatureCollection":
            feats = target.get("features", [])
            if not feats:
                return [68.0, 6.0, 98.0, 38.0]
            min_lon, min_lat = 180.0, 90.0
            max_lon, max_lat = -180.0, -90.0
            for f in feats:
                geom = f.get("geometry", {})
                b = extract_geometry_bbox(geom)
                if b != [0.0, 0.0, 0.0, 0.0]:
                    min_lon, min_lat = min(min_lon, b[0]), min(min_lat, b[1])
                    max_lon, max_lat = max(max_lon, b[2]), max(max_lat, b[3])
            return [round(min_lon, 6), round(min_lat, 6), round(max_lon, 6), round(max_lat, 6)]
        elif "type" in target and "coordinates" in target:
            return extract_geometry_bbox(target)

    raise ViewportCalculationError(f"Cannot calculate bounds for target: {type(target)}")


def calculate_viewport(
    target: Union[Dict[str, Any], GeoJSONFeature, GeoJSONFeatureCollection, List[float]],
    default_zoom: float = 8.5,
) -> MapViewport:
    """Calculates deterministic center and suggested zoom from geometry bounds."""
    bbox = calculate_bounds(target)
    min_lon, min_lat, max_lon, max_lat = bbox

    center_lon = round((min_lon + max_lon) / 2.0, 6)
    center_lat = round((min_lat + max_lat) / 2.0, 6)

    # Dynamic zoom estimation based on coordinate degree span
    lon_span = abs(max_lon - min_lon)
    lat_span = abs(max_lat - min_lat)
    max_span = max(lon_span, lat_span)

    if max_span == 0.0:
        zoom = 11.0  # Point coordinate
    elif max_span > 6.0:
        zoom = 5.5   # Country / Multi-State
    elif max_span > 2.5:
        zoom = 7.0   # State
    elif max_span > 0.8:
        zoom = 8.5   # District
    elif max_span > 0.2:
        zoom = 9.5   # Sub-District / Tehsil
    else:
        zoom = 11.0  # Localized

    return MapViewport(
        center=[center_lon, center_lat],
        zoom=zoom,
        pitch=0.0,
        bearing=0.0,
        bbox=bbox,
    )

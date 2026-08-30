"""Presentation-level Geometry Simplification Engine for Mobile Map Rendering.

Implements a deterministic Douglas-Peucker point decimation algorithm to optimize
mobile network payload sizes without mutating database source geometries.
"""

import math
from typing import Any, Dict, List
from app.gis.map.types import GeoJSONFeature, GeoJSONFeatureCollection


def _perpendicular_distance(point: List[float], line_start: List[float], line_end: List[float]) -> float:
    """Computes perpendicular distance from point (x, y) to line segment (x1, y1) -> (x2, y2)."""
    dx = line_end[0] - line_start[0]
    dy = line_end[1] - line_start[1]
    if dx == 0.0 and dy == 0.0:
        return math.hypot(point[0] - line_start[0], point[1] - line_start[1])

    numerator = abs(dy * point[0] - dx * point[1] + line_end[0] * line_start[1] - line_end[1] * line_start[0])
    denominator = math.hypot(dx, dy)
    return numerator / denominator


def simplify_polyline(points: List[List[float]], tolerance: float = 0.005) -> List[List[float]]:
    """Simplifies an open polyline using recursive Douglas-Peucker decimation."""
    if len(points) <= 2:
        return points

    dmax = 0.0
    index = 0
    end = len(points) - 1

    for i in range(1, end):
        d = _perpendicular_distance(points[i], points[0], points[end])
        if d > dmax:
            index = i
            dmax = d

    if dmax > tolerance:
        rec1 = simplify_polyline(points[: index + 1], tolerance)
        rec2 = simplify_polyline(points[index:], tolerance)
        return rec1[:-1] + rec2
    else:
        return [points[0], points[end]]


def simplify_ring(points: List[List[float]], tolerance: float = 0.005) -> List[List[float]]:
    """Simplifies a linear coordinate ring using Douglas-Peucker decimation."""
    if len(points) <= 4:
        return points

    # Find the point furthest from points[0] to split the closed ring into two stable halves
    furthest_idx = 0
    max_dist = 0.0
    for i in range(1, len(points) - 1):
        dist = math.hypot(points[i][0] - points[0][0], points[i][1] - points[0][1])
        if dist > max_dist:
            max_dist = dist
            furthest_idx = i

    if furthest_idx == 0:
        furthest_idx = len(points) // 2

    half1 = simplify_polyline(points[: furthest_idx + 1], tolerance)
    half2 = simplify_polyline(points[furthest_idx:], tolerance)

    merged = half1[:-1] + half2

    # A valid GeoJSON linear ring must have at least 4 coordinates (3 distinct + 1 closing)
    if len(merged) < 4:
        return points

    if merged[0] != merged[-1]:
        merged.append(merged[0])

    return merged


def simplify_geometry(geometry: Dict[str, Any], tolerance: float = 0.005) -> Dict[str, Any]:
    """Applies simplification to GeoJSON Polygon and MultiPolygon geometries."""
    g_type = geometry.get("type")
    coords = geometry.get("coordinates", [])

    if g_type == "Polygon":
        new_coords = [simplify_ring(ring, tolerance=tolerance) for ring in coords]
        return {"type": "Polygon", "coordinates": new_coords}
    elif g_type == "MultiPolygon":
        new_coords = [[simplify_ring(ring, tolerance=tolerance) for ring in poly] for poly in coords]
        return {"type": "MultiPolygon", "coordinates": new_coords}

    return geometry


def simplify_feature(feature: GeoJSONFeature, tolerance: float = 0.005) -> GeoJSONFeature:
    """Returns a simplified copy of a GeoJSON feature."""
    new_geom = simplify_geometry(feature.geometry, tolerance=tolerance)
    return GeoJSONFeature(
        id=feature.id,
        geometry=new_geom,
        properties=feature.properties,
    )


def simplify_feature_collection(
    collection: GeoJSONFeatureCollection,
    tolerance: float = 0.005,
) -> GeoJSONFeatureCollection:
    """Simplifies all features within a FeatureCollection for fast mobile transport."""
    simplified_features = [simplify_feature(f, tolerance=tolerance) for f in collection.features]
    return GeoJSONFeatureCollection(
        type="FeatureCollection",
        features=simplified_features,
        bbox=collection.bbox,
        metadata=collection.metadata,
    )

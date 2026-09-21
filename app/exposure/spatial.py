"""Spatial operations and geometric algorithms for VAYUBODHAK Phase 4.

Provides deterministic, high-precision geometric calculations in EPSG:4326:
- Geodesic spherical polygon area calculation (km²)
- Geodesic great-circle line length calculation (km)
- Robust point-in-polygon containment (Ray Casting with boundary inclusion)
- Line-polygon clipping & intersection length
- Polygon-polygon clipping (Sutherland-Hodgman algorithm)
- Bounding box indexing and validation
"""

import math
from typing import Any, Dict, List, Optional, Tuple

EARTH_RADIUS_KM = 6371.0088


# ============================================================================
# 1. Coordinate & Bounding Box Utilities
# ============================================================================

def validate_lon_lat(lon: float, lat: float) -> bool:
    """Validates geographic coordinates in WGS84."""
    return -180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0


def compute_bbox(coordinates: List[Tuple[float, float]]) -> Tuple[float, float, float, float]:
    """Computes bounding box (min_lon, min_lat, max_lon, max_lat) from coordinate sequence."""
    if not coordinates:
        raise ValueError("Cannot compute bounding box of empty coordinates")
    lons = [pt[0] for pt in coordinates]
    lats = [pt[1] for pt in coordinates]
    return (min(lons), min(lats), max(lons), max(lats))


def bbox_intersects(
    box1: Tuple[float, float, float, float],
    box2: Tuple[float, float, float, float],
) -> bool:
    """Checks whether two bounding boxes overlap."""
    min_lon1, min_lat1, max_lon1, max_lat1 = box1
    min_lon2, min_lat2, max_lon2, max_lat2 = box2
    return not (
        max_lon1 < min_lon2
        or min_lon1 > max_lon2
        or max_lat1 < min_lat2
        or min_lat1 > max_lat2
    )


# ============================================================================
# 2. Geodesic Distance and Length (Haversine)
# ============================================================================

def haversine_distance_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Computes great-circle distance between two points in kilometers."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_KM * c


def linestring_length_km(coords: List[Tuple[float, float]]) -> float:
    """Calculates total geodesic length of an ordered LineString in kilometers."""
    if len(coords) < 2:
        return 0.0
    total = 0.0
    for i in range(len(coords) - 1):
        total += haversine_distance_km(
            coords[i][0], coords[i][1], coords[i + 1][0], coords[i + 1][1]
        )
    return total


# ============================================================================
# 3. Geodesic Spherical Polygon Area
# ============================================================================

def spherical_polygon_area_sqkm(ring: List[Tuple[float, float]]) -> float:
    """Calculates geodesic area of a spherical polygon ring in square kilometers.

    Uses the spherical excess formula for a polygon on a sphere of radius R:
        Area = R² * |sum((lambda_{i+1} - lambda_{i-1}) * sin(phi_i)) / 2|
    """
    if len(ring) < 3:
        return 0.0

    # Ensure closed ring
    pts = list(ring)
    if pts[0] != pts[-1]:
        pts.append(pts[0])

    n = len(pts) - 1
    if n < 3:
        return 0.0

    total = 0.0
    for i in range(n):
        p_prev = pts[i - 1]
        p_curr = pts[i]
        p_next = pts[i + 1]

        lon_diff = math.radians(p_next[0]) - math.radians(p_prev[0])
        sin_lat = math.sin(math.radians(p_curr[1]))
        total += lon_diff * sin_lat

    area = (EARTH_RADIUS_KM ** 2) * abs(total) / 2.0
    return area


# ============================================================================
# 4. Point in Polygon Containment (Ray Casting)
# ============================================================================

def point_in_polygon(lon: float, lat: float, polygon_ring: List[Tuple[float, float]]) -> bool:
    """Tests if point (lon, lat) is inside or on the boundary of a polygon ring."""
    n = len(polygon_ring)
    if n < 3:
        return False

    # Check bounding box fast rejection
    lons = [p[0] for p in polygon_ring]
    lats = [p[1] for p in polygon_ring]
    if lon < min(lons) or lon > max(lons) or lat < min(lats) or lat > max(lats):
        return False

    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon_ring[i]
        xj, yj = polygon_ring[j]

        # Check vertex coincidence
        if abs(lon - xi) < 1e-9 and abs(lat - yi) < 1e-9:
            return True

        # Check if point lies exactly on horizontal edge
        if abs(yi - yj) < 1e-9 and abs(lat - yi) < 1e-9:
            if min(xi, xj) <= lon <= max(xi, xj):
                return True

        intersect = ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-15) + xi
        )
        if intersect:
            inside = not inside
        j = i

    return inside


def point_in_geojson(lon: float, lat: float, geometry: Dict[str, Any]) -> bool:
    """Evaluates containment of point in a GeoJSON Polygon or MultiPolygon."""
    gtype = geometry.get("type", "")
    coords = geometry.get("coordinates", [])

    if gtype == "Polygon":
        if not coords:
            return False
        # Outer ring
        outer_ring = [(pt[0], pt[1]) for pt in coords[0]]
        if not point_in_polygon(lon, lat, outer_ring):
            return False
        # Holes
        for hole in coords[1:]:
            hole_ring = [(pt[0], pt[1]) for pt in hole]
            if point_in_polygon(lon, lat, hole_ring):
                return False
        return True

    elif gtype == "MultiPolygon":
        for poly_coords in coords:
            if not poly_coords:
                continue
            outer_ring = [(pt[0], pt[1]) for pt in poly_coords[0]]
            if point_in_polygon(lon, lat, outer_ring):
                # Check holes
                in_hole = False
                for hole in poly_coords[1:]:
                    hole_ring = [(pt[0], pt[1]) for pt in hole]
                    if point_in_polygon(lon, lat, hole_ring):
                        in_hole = True
                        break
                if not in_hole:
                    return True
        return False

    return False


# ============================================================================
# 5. LineString & Polygon Clipping
# ============================================================================

def clip_segment_with_polygon(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    polygon_ring: List[Tuple[float, float]],
    num_samples: int = 20,
) -> float:
    """Approximates length of segment (p1, p2) falling within polygon in kilometers."""
    total_len = haversine_distance_km(p1[0], p1[1], p2[0], p2[1])
    if total_len == 0.0:
        return 0.0

    in1 = point_in_polygon(p1[0], p1[1], polygon_ring)
    in2 = point_in_polygon(p2[0], p2[1], polygon_ring)

    if in1 and in2:
        return total_len

    # Sample along segment
    inside_count = 0
    for step in range(num_samples + 1):
        t = step / float(num_samples)
        interp_lon = p1[0] + t * (p2[0] - p1[0])
        interp_lat = p1[1] + t * (p2[1] - p1[1])
        if point_in_polygon(interp_lon, interp_lat, polygon_ring):
            inside_count += 1

    ratio = inside_count / float(num_samples + 1)
    return round(total_len * ratio, 3)


def clip_linestring_with_polygon(
    coords: List[Tuple[float, float]],
    polygon_ring: List[Tuple[float, float]],
) -> float:
    """Calculates the exposed kilometer length of a LineString within a polygon."""
    if len(coords) < 2:
        return 0.0

    # Fast bbox rejection
    line_box = compute_bbox(coords)
    poly_box = compute_bbox(polygon_ring)
    if not bbox_intersects(line_box, poly_box):
        return 0.0

    intersected_km = 0.0
    for i in range(len(coords) - 1):
        intersected_km += clip_segment_with_polygon(
            coords[i], coords[i + 1], polygon_ring
        )
    return round(intersected_km, 3)


# ============================================================================
# 6. Sutherland-Hodgman Polygon-Polygon Clipping (Convex / Simple)
# ============================================================================

def _is_inside_edge(
    cp1: Tuple[float, float],
    cp2: Tuple[float, float],
    p: Tuple[float, float],
) -> bool:
    """Tests if point p is on the inside (left) of directed edge cp1 -> cp2."""
    return (cp2[0] - cp1[0]) * (p[1] - cp1[1]) - (cp2[1] - cp1[1]) * (p[0] - cp1[0]) >= 0


def _compute_intersection(
    cp1: Tuple[float, float],
    cp2: Tuple[float, float],
    s: Tuple[float, float],
    e: Tuple[float, float],
) -> Tuple[float, float]:
    """Computes coordinate intersection of line cp1-cp2 and segment s-e."""
    dc = (cp1[0] - cp2[0], cp1[1] - cp2[1])
    dp = (s[0] - e[0], s[1] - e[1])
    n1 = cp1[0] * cp2[1] - cp1[1] * cp2[0]
    n2 = s[0] * e[1] - s[1] * e[0]
    denom = dc[0] * dp[1] - dc[1] * dp[0]
    if abs(denom) < 1e-12:
        return s
    x = (n1 * dp[0] - n2 * dc[0]) / denom
    y = (n1 * dp[1] - n2 * dc[1]) / denom
    return (x, y)


def _polygon_signed_area(pts: List[Tuple[float, float]]) -> float:
    """Calculates 2D planar signed area for winding order determination."""
    area = 0.0
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        area += pts[i][0] * pts[j][1] - pts[j][0] * pts[i][1]
    return area / 2.0


def _ensure_ccw(pts: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Ensures polygon coordinates are counter-clockwise (CCW) wound."""
    open_pts = pts[:-1] if pts and pts[0] == pts[-1] else list(pts)
    if len(open_pts) < 3:
        return pts
    if _polygon_signed_area(open_pts) < 0:
        open_pts.reverse()
    return open_pts + [open_pts[0]]


def clip_polygon_with_polygon(
    subject_poly: List[Tuple[float, float]],
    clip_poly: List[Tuple[float, float]],
) -> List[Tuple[float, float]]:
    """Clips subject_poly by clip_poly using Sutherland-Hodgman polygon clipping."""
    s_ccw = _ensure_ccw(subject_poly)
    c_ccw = _ensure_ccw(clip_poly)

    s_pts = s_ccw[:-1]
    c_pts = c_ccw[:-1]

    if len(s_pts) < 3 or len(c_pts) < 3:
        return []

    output_list = s_pts

    for i in range(len(c_pts)):
        cp1 = c_pts[i]
        cp2 = c_pts[(i + 1) % len(c_pts)]

        input_list = output_list
        output_list = []
        if not input_list:
            break

        s = input_list[-1]
        for e in input_list:
            if _is_inside_edge(cp1, cp2, e):
                if not _is_inside_edge(cp1, cp2, s):
                    output_list.append(_compute_intersection(cp1, cp2, s, e))
                output_list.append(e)
            elif _is_inside_edge(cp1, cp2, s):
                output_list.append(_compute_intersection(cp1, cp2, s, e))
            s = e

    if len(output_list) < 3:
        return []

    # Close the ring
    output_list.append(output_list[0])
    return output_list


def compute_polygon_intersection_area_sqkm(
    poly1: List[Tuple[float, float]],
    poly2: List[Tuple[float, float]],
) -> float:
    """Calculates the geodesic overlapping area (km²) between two polygon rings."""
    # Fast Bounding Box rejection
    box1 = compute_bbox(poly1)
    box2 = compute_bbox(poly2)
    if not bbox_intersects(box1, box2):
        return 0.0

    area1 = spherical_polygon_area_sqkm(poly1)
    area2 = spherical_polygon_area_sqkm(poly2)
    if area1 == 0.0 or area2 == 0.0:
        return 0.0

    p1_open = poly1[:-1] if poly1 and poly1[0] == poly1[-1] else poly1
    p2_open = poly2[:-1] if poly2 and poly2[0] == poly2[-1] else poly2

    # Check complete containment of poly2 inside poly1
    if all(point_in_polygon(p[0], p[1], poly1) for p in p2_open):
        return round(area2, 3)

    # Check complete containment of poly1 inside poly2
    if all(point_in_polygon(p[0], p[1], poly2) for p in p1_open):
        return round(area1, 3)

    # Perform Sutherland-Hodgman clipping
    clipped = clip_polygon_with_polygon(poly1, poly2)
    if len(clipped) < 3:
        clipped = clip_polygon_with_polygon(poly2, poly1)
        if len(clipped) < 3:
            return 0.0

    raw_inter_area = spherical_polygon_area_sqkm(clipped)
    # Physically, intersection area can never exceed the smaller of the two inputs
    max_possible = min(area1, area2)
    return round(min(raw_inter_area, max_possible), 3)


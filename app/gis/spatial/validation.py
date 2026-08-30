"""Deterministic spatial validation functions for coordinates, GeoJSON geometries, and bounding boxes."""

from typing import Any, Dict, List, Sequence, Union

from app.gis.spatial.errors import InvalidCoordinatesError, InvalidGeometryError
from app.gis.spatial.types import BoundingBoxInput, GeoJSONGeometryInput, SpatialPointInput

# Approximate bounding box for Indian Territory (WGS84)
INDIA_BOUNDING_BOX = {
    "min_lat": 6.0,
    "max_lat": 38.0,
    "min_lon": 68.0,
    "max_lon": 98.0,
}


def validate_coordinates(
    lat: Union[float, int],
    lon: Union[float, int],
    enforce_india_bounds: bool = False,
) -> SpatialPointInput:
    """Validates geographic coordinates in WGS84 (EPSG:4326).

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        enforce_india_bounds: If True, asserts coordinates fall within Indian subcontinental bbox.

    Returns:
        SpatialPointInput: Validated point.

    Raises:
        InvalidCoordinatesError: If coordinates are out of physical or regional bounds.
    """
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError) as exc:
        raise InvalidCoordinatesError(f"Coordinates must be numeric: lat={lat!r}, lon={lon!r}") from exc

    if not (-90.0 <= lat_f <= 90.0):
        raise InvalidCoordinatesError(f"Latitude out of bounds [-90, 90]: {lat_f}")

    if not (-180.0 <= lon_f <= 180.0):
        raise InvalidCoordinatesError(f"Longitude out of bounds [-180, 180]: {lon_f}")

    if enforce_india_bounds:
        if not (INDIA_BOUNDING_BOX["min_lat"] <= lat_f <= INDIA_BOUNDING_BOX["max_lat"]) or not (
            INDIA_BOUNDING_BOX["min_lon"] <= lon_f <= INDIA_BOUNDING_BOX["max_lon"]
        ):
            raise InvalidCoordinatesError(
                f"Coordinates ({lat_f}, {lon_f}) fall outside the Indian geographic domain "
                f"({INDIA_BOUNDING_BOX['min_lat']}°N-{INDIA_BOUNDING_BOX['max_lat']}°N, "
                f"{INDIA_BOUNDING_BOX['min_lon']}°E-{INDIA_BOUNDING_BOX['max_lon']}°E)"
            )

    return SpatialPointInput(latitude=lat_f, longitude=lon_f)


def _validate_coordinate_pair(pair: Sequence[Any], path: str = "coordinate") -> None:
    """Validates that a coordinate pair is strictly [longitude, latitude]."""
    if not isinstance(pair, (list, tuple)) or len(pair) < 2:
        raise InvalidGeometryError(f"Malformed coordinate at {path}: expected [longitude, latitude] pair, got {pair!r}")

    lon, lat = pair[0], pair[1]
    try:
        lon_f = float(lon)
        lat_f = float(lat)
    except (TypeError, ValueError) as exc:
        raise InvalidGeometryError(f"Non-numeric coordinates at {path}: [{lon!r}, {lat!r}]") from exc

    if not (-180.0 <= lon_f <= 180.0):
        raise InvalidCoordinatesError(f"Longitude out of bounds [-180, 180] at {path}: {lon_f}")

    if not (-90.0 <= lat_f <= 90.0):
        raise InvalidCoordinatesError(f"Latitude out of bounds [-90, 90] at {path}: {lat_f}")


def _validate_linear_ring(ring: Sequence[Any], ring_idx: int = 0) -> None:
    """Validates a closed GeoJSON linear ring."""
    if not isinstance(ring, (list, tuple)):
        raise InvalidGeometryError(f"Linear ring {ring_idx} must be an array of coordinates")

    if len(ring) < 4:
        raise InvalidGeometryError(
            f"Linear ring {ring_idx} must contain at least 4 coordinate vertices (got {len(ring)})"
        )

    for v_idx, vertex in enumerate(ring):
        _validate_coordinate_pair(vertex, path=f"ring[{ring_idx}].vertex[{v_idx}]")

    # Verify closure: first vertex == last vertex
    first, last = ring[0], ring[-1]
    if first[0] != last[0] or first[1] != last[1]:
        raise InvalidGeometryError(
            f"Linear ring {ring_idx} is not closed: first vertex {first} != last vertex {last}"
        )


def validate_geojson_geometry(data: Dict[str, Any]) -> GeoJSONGeometryInput:
    """Validates RFC 7946 GeoJSON geometry objects (Point, Polygon, MultiPolygon).

    Enforces [longitude, latitude] coordinate ordering and topological ring closure.

    Args:
        data: Raw GeoJSON dictionary with 'type' and 'coordinates'.

    Returns:
        GeoJSONGeometryInput: Validated geometry object.

    Raises:
        InvalidGeometryError: If structure or topological constraints are violated.
        InvalidCoordinatesError: If individual vertex coordinates exceed bounds.
    """
    if not isinstance(data, dict):
        raise InvalidGeometryError(f"GeoJSON geometry must be a dictionary, got {type(data).__name__}")

    geom_type = data.get("type")
    if geom_type not in ("Point", "Polygon", "MultiPolygon"):
        raise InvalidGeometryError(f"Unsupported geometry type {geom_type!r}. Supported: Point, Polygon, MultiPolygon")

    coords = data.get("coordinates")
    if coords is None:
        raise InvalidGeometryError("GeoJSON geometry missing required 'coordinates' field")

    if geom_type == "Point":
        _validate_coordinate_pair(coords, path="point")

    elif geom_type == "Polygon":
        if not isinstance(coords, (list, tuple)) or len(coords) == 0:
            raise InvalidGeometryError("Polygon coordinates must be a non-empty array of linear rings")
        for r_idx, ring in enumerate(coords):
            _validate_linear_ring(ring, ring_idx=r_idx)

    elif geom_type == "MultiPolygon":
        if not isinstance(coords, (list, tuple)) or len(coords) == 0:
            raise InvalidGeometryError("MultiPolygon coordinates must be a non-empty array of polygons")
        for p_idx, poly in enumerate(coords):
            if not isinstance(poly, (list, tuple)) or len(poly) == 0:
                raise InvalidGeometryError(f"MultiPolygon polygon {p_idx} must be an array of linear rings")
            for r_idx, ring in enumerate(poly):
                _validate_linear_ring(ring, ring_idx=r_idx)

    return GeoJSONGeometryInput(type=geom_type, coordinates=coords)


def validate_bounding_box(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
) -> BoundingBoxInput:
    """Validates a spatial bounding box envelope.

    Args:
        min_lat: South latitude boundary (-90 to 90).
        min_lon: West longitude boundary (-180 to 180).
        max_lat: North latitude boundary (-90 to 90).
        max_lon: East longitude boundary (-180 to 180).

    Returns:
        BoundingBoxInput: Validated bounding box.

    Raises:
        InvalidCoordinatesError: If coordinate values are out of bounds or inverted.
    """
    try:
        min_lat_f = float(min_lat)
        min_lon_f = float(min_lon)
        max_lat_f = float(max_lat)
        max_lon_f = float(max_lon)
    except (TypeError, ValueError) as exc:
        raise InvalidCoordinatesError(f"Bounding box coordinates must be numeric") from exc

    if not (-90.0 <= min_lat_f <= 90.0) or not (-90.0 <= max_lat_f <= 90.0):
        raise InvalidCoordinatesError(f"Latitude out of bounds [-90, 90]: min={min_lat_f}, max={max_lat_f}")

    if not (-180.0 <= min_lon_f <= 180.0) or not (-180.0 <= max_lon_f <= 180.0):
        raise InvalidCoordinatesError(f"Longitude out of bounds [-180, 180]: min={min_lon_f}, max={max_lon_f}")

    if min_lat_f > max_lat_f:
        raise InvalidCoordinatesError(f"Inverted latitude bounds: min_lat ({min_lat_f}) > max_lat ({max_lat_f})")

    if min_lon_f > max_lon_f:
        raise InvalidCoordinatesError(f"Inverted longitude bounds: min_lon ({min_lon_f}) > max_lon ({max_lon_f})")

    return BoundingBoxInput(
        min_lat=min_lat_f,
        min_lon=min_lon_f,
        max_lat=max_lat_f,
        max_lon=max_lon_f,
    )

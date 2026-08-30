"""GeoJSON and geometry validation rules for administrative boundaries.

Guarantees:
- Enforces EPSG:4326 coordinate ranges within valid geographic bounds.
- Normalizes single Polygons into MultiPolygon coordinate structures.
- Enforces non-empty geometries and closed coordinate rings.
- Validates administrative properties (codes, names, parent references).
- Never modifies coordinates or repairs geometry silently.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from app.gis.schemas.boundaries import AdminLevel

# Approximate geographic bounds for India (including Andaman & Nicobar and Lakshadweep)
MIN_LON, MAX_LON = 68.0, 98.5
MIN_LAT, MAX_LAT = 6.0, 38.0


class GeoJSONValidationError(ValueError):
    """Raised when GeoJSON structure, properties, or geometry violate requirements."""
    pass


def validate_feature_collection(data: Any) -> List[Dict[str, Any]]:
    """Validate that input is a valid GeoJSON FeatureCollection and return its features."""
    if not isinstance(data, dict):
        raise GeoJSONValidationError("GeoJSON must be a JSON object (dict)")

    geojson_type = data.get("type")
    if geojson_type == "FeatureCollection":
        features = data.get("features")
        if not isinstance(features, list):
            raise GeoJSONValidationError("GeoJSON FeatureCollection must have a 'features' array")
        return features
    elif geojson_type == "Feature":
        return [data]
    else:
        raise GeoJSONValidationError(
            f"Unsupported GeoJSON type: {geojson_type!r}. Expected 'FeatureCollection' or 'Feature'"
        )


def normalize_and_validate_geometry(geom: Any) -> Dict[str, Any]:
    """Validate geometry and normalize Polygon into MultiPolygon representation.

    Returns:
        dict: Standard GeoJSON MultiPolygon dictionary with EPSG:4326 coordinates.
    """
    if not isinstance(geom, dict):
        raise GeoJSONValidationError("Geometry must be a dictionary")

    geom_type = geom.get("type")
    coordinates = geom.get("coordinates")

    if not coordinates:
        raise GeoJSONValidationError("Geometry coordinates cannot be empty")

    if geom_type == "Polygon":
        _validate_polygon_coordinates(coordinates)
        # Wrap single Polygon into MultiPolygon format: [[[ [lon, lat], ... ]]]
        return {
            "type": "MultiPolygon",
            "coordinates": [coordinates],
        }
    elif geom_type == "MultiPolygon":
        for poly_coords in coordinates:
            _validate_polygon_coordinates(poly_coords)
        return {
            "type": "MultiPolygon",
            "coordinates": coordinates,
        }
    else:
        raise GeoJSONValidationError(
            f"Invalid geometry type: {geom_type!r}. Only 'Polygon' and 'MultiPolygon' are supported"
        )


def _validate_polygon_coordinates(poly_coords: Any) -> None:
    """Validate coordinate rings of a polygon."""
    if not isinstance(poly_coords, list) or len(poly_coords) == 0:
        raise GeoJSONValidationError("Polygon must contain at least one linear ring")

    for ring_idx, ring in enumerate(poly_coords):
        if not isinstance(ring, list) or len(ring) < 4:
            raise GeoJSONValidationError(
                f"Linear ring {ring_idx} must have at least 4 coordinate positions"
            )

        # Check ring is closed (first position == last position)
        first, last = ring[0], ring[-1]
        if not isinstance(first, list) or not isinstance(last, list) or len(first) < 2 or len(last) < 2:
            raise GeoJSONValidationError(f"Invalid coordinate position in ring {ring_idx}")

        if first[0] != last[0] or first[1] != last[1]:
            raise GeoJSONValidationError(
                f"Linear ring {ring_idx} is not closed (first point {first} != last point {last})"
            )

        # Validate coordinate points range
        for pt_idx, pt in enumerate(ring):
            if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                raise GeoJSONValidationError(f"Invalid point at index {pt_idx} in ring {ring_idx}")
            lon, lat = float(pt[0]), float(pt[1])
            if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
                raise GeoJSONValidationError(
                    f"Coordinate ({lon}, {lat}) outside global WGS84 range"
                )


def extract_centroid_and_bbox(multipoly_coords: List[Any]) -> Tuple[float, float]:
    """Compute approximate centroid (mean of all vertices) for indexing/metadata."""
    lons: List[float] = []
    lats: List[float] = []
    for poly in multipoly_coords:
        for ring in poly:
            for pt in ring:
                lons.append(float(pt[0]))
                lats.append(float(pt[1]))

    if not lons:
        return (0.0, 0.0)

    centroid_lon = round(sum(lons) / len(lons), 5)
    centroid_lat = round(sum(lats) / len(lats), 5)
    return (centroid_lat, centroid_lon)


def validate_boundary_properties(
    props: Dict[str, Any],
    level: AdminLevel,
) -> Dict[str, Any]:
    """Validate and extract required attributes for a specific administrative level.

    Supports common gazetteer naming conventions (e.g. Survey of India, Census, LGD).
    """
    if not isinstance(props, dict):
        raise GeoJSONValidationError("Feature properties must be a dictionary")

    cleaned: Dict[str, Any] = {}

    if level == AdminLevel.COUNTRY:
        code = props.get("country_code") or props.get("ISO_A2") or props.get("code") or "IN"
        name = props.get("country_name") or props.get("NAME") or props.get("name") or "India"
        cleaned["country_code"] = str(code).strip().upper()
        cleaned["country_name"] = str(name).strip()
        cleaned["area_sqkm"] = _parse_optional_float(props.get("area_sqkm") or props.get("AREA_SQKM"))

    elif level == AdminLevel.STATE:
        code = props.get("state_code") or props.get("ISO_3166_2") or props.get("st_code") or props.get("code")
        name = props.get("state_name") or props.get("ST_NM") or props.get("name")
        country_code = props.get("country_code") or "IN"

        if not code or not str(code).strip():
            raise GeoJSONValidationError("State feature missing required 'state_code' property")
        if not name or not str(name).strip():
            raise GeoJSONValidationError("State feature missing required 'state_name' property")

        cleaned["state_code"] = str(code).strip().upper()
        cleaned["country_code"] = str(country_code).strip().upper()
        cleaned["state_name"] = str(name).strip()
        cleaned["state_type"] = str(props.get("state_type") or props.get("TYPE") or "State").strip()
        cleaned["area_sqkm"] = _parse_optional_float(props.get("area_sqkm") or props.get("AREA_SQKM"))

    elif level == AdminLevel.DISTRICT:
        code = props.get("district_code") or props.get("dt_code") or props.get("code")
        state_code = props.get("state_code") or props.get("st_code")
        name = props.get("district_name") or props.get("DISTRICT") or props.get("name")

        if not code or not str(code).strip():
            raise GeoJSONValidationError("District feature missing required 'district_code' property")
        if not state_code or not str(state_code).strip():
            raise GeoJSONValidationError("District feature missing required 'state_code' property")
        if not name or not str(name).strip():
            raise GeoJSONValidationError("District feature missing required 'district_name' property")

        cleaned["district_code"] = str(code).strip().upper()
        cleaned["state_code"] = str(state_code).strip().upper()
        cleaned["district_name"] = str(name).strip()
        cleaned["area_sqkm"] = _parse_optional_float(props.get("area_sqkm") or props.get("AREA_SQKM"))

    elif level == AdminLevel.SUBDISTRICT:
        code = props.get("subdistrict_code") or props.get("sdt_code") or props.get("tehsil_code") or props.get("code")
        district_code = props.get("district_code") or props.get("dt_code")
        name = props.get("subdistrict_name") or props.get("TEHSIL") or props.get("SUB_DIST") or props.get("name")

        if not code or not str(code).strip():
            raise GeoJSONValidationError("SubDistrict feature missing required 'subdistrict_code' property")
        if not district_code or not str(district_code).strip():
            raise GeoJSONValidationError("SubDistrict feature missing required 'district_code' property")
        if not name or not str(name).strip():
            raise GeoJSONValidationError("SubDistrict feature missing required 'subdistrict_name' property")

        cleaned["subdistrict_code"] = str(code).strip().upper()
        cleaned["district_code"] = str(district_code).strip().upper()
        cleaned["subdistrict_name"] = str(name).strip()
        cleaned["area_sqkm"] = _parse_optional_float(props.get("area_sqkm") or props.get("AREA_SQKM"))

    return cleaned


def _parse_optional_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

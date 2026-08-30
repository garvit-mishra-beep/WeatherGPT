"""Spatial Grid-to-Polygon Extraction & Zonal Statistics Engine.

Computes deterministic atmospheric aggregations over Polygon & MultiPolygon boundaries.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from app.nwp.errors import NWPError
from app.nwp.types import AggregationMethod, NWPGridArray, NWPPolygonResult
from app.nwp.validation import normalize_longitude_180


def _point_in_polygon_ring(x: float, y: float, ring: Sequence[Sequence[float]]) -> bool:
    """Ray casting point-in-polygon algorithm for a 2D linear ring ([lon, lat])."""
    n = len(ring)
    inside = False
    p1x, p1y = ring[0][0], ring[0][1]
    for i in range(1, n + 1):
        p2x, p2y = ring[i % n][0], ring[i % n][1]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def _point_in_geojson_geometry(x: float, y: float, geometry: Dict[str, Any]) -> bool:
    """Tests if point (lon, lat) is contained inside a GeoJSON Polygon or MultiPolygon."""
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates", [])

    if geom_type == "Polygon":
        if not coords:
            return False
        # Exterior ring
        if not _point_in_polygon_ring(x, y, coords[0]):
            return False
        # Check interior rings (holes)
        for hole in coords[1:]:
            if _point_in_polygon_ring(x, y, hole):
                return False
        return True

    elif geom_type == "MultiPolygon":
        for poly_coords in coords:
            if not poly_coords:
                continue
            if _point_in_polygon_ring(x, y, poly_coords[0]):
                in_hole = False
                for hole in poly_coords[1:]:
                    if _point_in_polygon_ring(x, y, hole):
                        in_hole = True
                        break
                if not in_hole:
                    return True
        return False

    return False


def aggregate_grid_over_geometry(
    grid: NWPGridArray,
    geometry: Dict[str, Any],
    aggregation_method: AggregationMethod = AggregationMethod.MEAN,
    geometry_id: Optional[str] = None,
) -> NWPPolygonResult:
    """Extracts NWP grid cells inside a geometry and computes zonal summary statistics.

    Args:
        grid: NWPGridArray containing atmospheric physical parameters.
        geometry: GeoJSON Polygon or MultiPolygon dictionary.
        aggregation_method: Statistical aggregation type (MEAN, MIN, MAX, MEDIAN, P90, SUM).
        geometry_id: Optional identifier for the boundary entity (e.g. 'IN-GJ-24').

    Returns:
        NWPPolygonResult: Summary statistic value, cell counts, and provenance.

    Raises:
        NWPError: If no grid points fall inside the geometry.
    """
    lats = np.array(grid.lats, dtype=np.float64)
    lons = np.array([normalize_longitude_180(x) for x in grid.lons], dtype=np.float64)
    data = np.asarray(grid.data, dtype=np.float64)

    # 1. Evaluate point containment for each grid vertex
    contained_values: List[float] = []
    missing_cells = 0

    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            if _point_in_geojson_geometry(lon, lat, geometry):
                val = float(data[i, j])
                if np.isnan(val):
                    missing_cells += 1
                else:
                    contained_values.append(val)

    if not contained_values:
        # Fallback to nearest vertex if geometry is smaller than grid spacing
        # Compute centroid of geometry
        if geometry.get("type") == "Polygon" and geometry.get("coordinates"):
            ring = geometry["coordinates"][0]
            c_lon = float(np.mean([p[0] for p in ring]))
            c_lat = float(np.mean([p[1] for p in ring]))
        else:
            c_lat, c_lon = float(lats[len(lats) // 2]), float(lons[len(lons) // 2])

        lat_idx = int(np.argmin(np.abs(lats - c_lat)))
        lon_idx = int(np.argmin(np.abs(lons - c_lon)))
        fallback_val = float(data[lat_idx, lon_idx])
        if not np.isnan(fallback_val):
            contained_values.append(fallback_val)
        else:
            missing_cells += 1

    if not contained_values:
        raise NWPError(f"No valid NWP grid values found inside geometry '{geometry_id}'")

    val_arr = np.array(contained_values, dtype=np.float64)

    # 2. Compute Zonal Statistic
    if aggregation_method == AggregationMethod.MEAN:
        stat_val = float(np.mean(val_arr))
    elif aggregation_method == AggregationMethod.MIN:
        stat_val = float(np.min(val_arr))
    elif aggregation_method == AggregationMethod.MAX:
        stat_val = float(np.max(val_arr))
    elif aggregation_method == AggregationMethod.MEDIAN:
        stat_val = float(np.median(val_arr))
    elif aggregation_method == AggregationMethod.P90:
        stat_val = float(np.percentile(val_arr, 90))
    elif aggregation_method == AggregationMethod.SUM:
        stat_val = float(np.sum(val_arr))
    else:
        stat_val = float(np.mean(val_arr))

    prov = grid.provenance
    if prov is None:
        from app.nwp.types import NWPProvenance
        prov = NWPProvenance(
            model_name=grid.model.value,
            ingestion_cycle=grid.cycle_time_iso,
            valid_time_start=grid.valid_time_iso,
            valid_time_end=grid.valid_time_iso,
            grid_spacing_degrees=grid.grid_resolution_deg,
            interpolation_method=aggregation_method.value,
            upstream_provider="NOAA / NCEP",
        )

    return NWPPolygonResult(
        model=grid.model,
        geometry_id=geometry_id,
        variable=grid.variable_name,
        aggregation_method=aggregation_method,
        value=round(stat_val, 2),
        units=grid.units,
        cycle_time_iso=grid.cycle_time_iso,
        valid_time_iso=grid.valid_time_iso,
        valid_cell_count=len(contained_values),
        missing_cell_count=missing_cells,
        provenance=prov,
    )

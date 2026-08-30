"""Deterministic Grid-to-Point Interpolation Engine (Bilinear & Nearest-Neighbor).

Adheres strictly to docs/08_NWP_SPEC.md §4.1.
"""

import math
from typing import Tuple, Union
import numpy as np

from app.nwp.errors import NWPInterpolationError, NWPOutsideGridError
from app.nwp.types import InterpolationMethod, NWPGridArray
from app.nwp.validation import assert_point_in_grid, normalize_longitude_180


def _find_bounding_indices(coords: np.ndarray, val: float) -> Tuple[int, int]:
    """Finds the two surrounding indices (i1, i2) such that coords[i1] <= val <= coords[i2] or vice-versa.

    Handles both ascending and descending 1D coordinate arrays.
    """
    is_ascending = coords[0] < coords[-1]

    if is_ascending:
        idx = np.searchsorted(coords, val, side="right") - 1
        i1 = max(0, min(len(coords) - 2, int(idx)))
        i2 = i1 + 1
    else:
        # Descending coordinates (e.g. lat from 38 down to 6)
        idx = np.searchsorted(-coords, -val, side="right") - 1
        i1 = max(0, min(len(coords) - 2, int(idx)))
        i2 = i1 + 1

    return i1, i2


def interpolate_bilinear(grid: NWPGridArray, lat: float, lon: float) -> float:
    """Executes mathematically exact 2D Bilinear Interpolation over an NWP grid slice.

    Equation (docs/08_NWP_SPEC.md §4.1):
        f(x, y) = [ (x2 - x)(y2 - y) f(Q11) + (x - x1)(y2 - y) f(Q21)
                  + (x2 - x)(y - y1) f(Q12) + (x - x1)(y - y1) f(Q22) ] / [ (x2 - x1)(y2 - y1) ]

    Args:
        grid: NWPGridArray containing 2D data array and 1D lat/lon coordinates.
        lat: Target latitude in decimal degrees.
        lon: Target longitude in decimal degrees.

    Returns:
        float: Interpolated atmospheric parameter value.

    Raises:
        NWPOutsideGridError: If coordinates are outside grid bounds.
        NWPInterpolationError: If neighboring grid cells contain NaN / missing values.
    """
    lats = np.array(grid.lats, dtype=np.float64)
    lons = np.array([normalize_longitude_180(x) for x in grid.lons], dtype=np.float64)
    norm_lon = normalize_longitude_180(lon)

    lat_min, lat_max = float(np.min(lats)), float(np.max(lats))
    lon_min, lon_max = float(np.min(lons)), float(np.max(lons))
    assert_point_in_grid(lat, norm_lon, lat_min, lat_max, lon_min, lon_max)

    data = np.asarray(grid.data, dtype=np.float64)

    # 1. Check exact vertex hit
    lat_exact = np.where(np.isclose(lats, lat, atol=1e-5))[0]
    lon_exact = np.where(np.isclose(lons, norm_lon, atol=1e-5))[0]
    if len(lat_exact) > 0 and len(lon_exact) > 0:
        val = data[lat_exact[0], lon_exact[0]]
        if np.isnan(val):
            raise NWPInterpolationError(f"Grid vertex at ({lat}, {norm_lon}) contains NaN / missing data")
        return round(float(val), 3)

    # 2. Find bounding index intervals
    i1, i2 = _find_bounding_indices(lats, lat)
    j1, j2 = _find_bounding_indices(lons, norm_lon)

    y1, y2 = float(lats[i1]), float(lats[i2])
    x1, x2 = float(lons[j1]), float(lons[j2])

    # 3. Extract 4 surrounding corner values
    # Q11 = (x1, y1), Q21 = (x2, y1), Q12 = (x1, y2), Q22 = (x2, y2)
    q11 = float(data[i1, j1])
    q21 = float(data[i1, j2])
    q12 = float(data[i2, j1])
    q22 = float(data[i2, j2])

    # 4. Check for missing data in corners
    if any(np.isnan([q11, q21, q12, q22])):
        raise NWPInterpolationError(
            f"Bilinear interpolation failed: neighboring cells for ({lat:.4f}, {norm_lon:.4f}) contain NaN"
        )

    # 5. Execute 2D Bilinear Weighting
    denom = (x2 - x1) * (y2 - y1)
    if abs(denom) < 1e-9:
        return round(q11, 3)

    term1 = (x2 - norm_lon) * (y2 - lat) * q11
    term2 = (norm_lon - x1) * (y2 - lat) * q21
    term3 = (x2 - norm_lon) * (lat - y1) * q12
    term4 = (norm_lon - x1) * (lat - y1) * q22

    result = (term1 + term2 + term3 + term4) / denom
    return round(float(result), 3)


def interpolate_nearest_neighbor(grid: NWPGridArray, lat: float, lon: float) -> float:
    """Extracts the value of the nearest grid vertex in the NWP array."""
    lats = np.array(grid.lats, dtype=np.float64)
    lons = np.array([normalize_longitude_180(x) for x in grid.lons], dtype=np.float64)
    norm_lon = normalize_longitude_180(lon)

    lat_min, lat_max = float(np.min(lats)), float(np.max(lats))
    lon_min, lon_max = float(np.min(lons)), float(np.max(lons))
    assert_point_in_grid(lat, norm_lon, lat_min, lat_max, lon_min, lon_max)

    lat_idx = int(np.argmin(np.abs(lats - lat)))
    lon_idx = int(np.argmin(np.abs(lons - norm_lon)))

    data = np.asarray(grid.data, dtype=np.float64)
    val = data[lat_idx, lon_idx]

    if np.isnan(val):
        raise NWPInterpolationError(f"Nearest grid vertex for ({lat}, {norm_lon}) contains NaN")

    return round(float(val), 3)


def interpolate_point(
    grid: NWPGridArray,
    lat: float,
    lon: float,
    method: InterpolationMethod = InterpolationMethod.BILINEAR,
) -> float:
    """Unified grid-to-point interpolation dispatcher."""
    if method == InterpolationMethod.BILINEAR:
        return interpolate_bilinear(grid, lat, lon)
    elif method == InterpolationMethod.NEAREST_NEIGHBOR:
        return interpolate_nearest_neighbor(grid, lat, lon)
    raise NWPInterpolationError(f"Unsupported interpolation method: {method}")

"""Grid validation, coordinate checking, and longitude normalization for NWP arrays."""

from typing import List, Sequence, Tuple, Union
import numpy as np

from app.nwp.errors import NWPGridValidationError, NWPOutsideGridError

# Indian Subcontinent Meteorological Extent (docs/08_NWP_SPEC.md §4)
INDIA_NWP_BOUNDS = {
    "min_lat": 6.0,
    "max_lat": 38.0,
    "min_lon": 68.0,
    "max_lon": 98.0,
}


def normalize_longitude_180(lon: float) -> float:
    """Normalizes longitude to the standard [-180, 180] degree domain.

    Converts [0, 360) degree conventions (common in GFS/NCEP files) to [-180, 180].
    """
    normalized = ((lon + 180.0) % 360.0) - 180.0
    # Handle exact 180.0 edge case
    if normalized == -180.0 and lon > 0:
        return 180.0
    return round(normalized, 6)


def validate_nwp_coordinates(
    lats: Sequence[float],
    lons: Sequence[float],
    expected_resolution: float = 0.25,
) -> Tuple[np.ndarray, np.ndarray]:
    """Validates NWP 1D coordinate arrays for monotonicity, bounds, and spacing.

    Args:
        lats: Sequence of latitude coordinates in degrees North.
        lons: Sequence of longitude coordinates in degrees East.
        expected_resolution: Expected grid spacing in degrees (default: 0.25°).

    Returns:
        Tuple[np.ndarray, np.ndarray]: Validated (lats, lons) as float NumPy arrays.

    Raises:
        NWPGridValidationError: If coordinates are non-monotonic, out-of-bounds, or misaligned.
    """
    if len(lats) < 2:
        raise NWPGridValidationError(f"Latitude coordinate array must have at least 2 points (got {len(lats)})")
    if len(lons) < 2:
        raise NWPGridValidationError(f"Longitude coordinate array must have at least 2 points (got {len(lons)})")

    lat_arr = np.array(lats, dtype=np.float64)
    # Normalize longitudes if supplied in 0-360 range
    lon_arr = np.array([normalize_longitude_180(x) for x in lons], dtype=np.float64)

    # Check physical latitude bounds [-90, 90]
    if np.any(lat_arr < -90.0) or np.any(lat_arr > 90.0):
        raise NWPGridValidationError(f"Latitude values out of physical bounds [-90, 90]: min={lat_arr.min()}, max={lat_arr.max()}")

    # Check physical longitude bounds [-180, 180]
    if np.any(lon_arr < -180.0) or np.any(lon_arr > 180.0):
        raise NWPGridValidationError(f"Longitude values out of physical bounds [-180, 180]: min={lon_arr.min()}, max={lon_arr.max()}")

    # Check latitude monotonicity (either strictly increasing or strictly decreasing)
    lat_diffs = np.diff(lat_arr)
    is_lat_inc = np.all(lat_diffs > 0)
    is_lat_dec = np.all(lat_diffs < 0)
    if not (is_lat_inc or is_lat_dec):
        raise NWPGridValidationError("Latitude coordinates must be strictly monotonic (ascending or descending)")

    # Check longitude monotonicity (strictly increasing)
    lon_diffs = np.diff(lon_arr)
    if not np.all(lon_diffs > 0):
        raise NWPGridValidationError("Longitude coordinates must be strictly monotonically increasing")

    # Check grid spacing tolerance
    lat_spacing = np.abs(lat_diffs)
    lon_spacing = np.abs(lon_diffs)
    if not np.allclose(lat_spacing, expected_resolution, atol=0.01):
        raise NWPGridValidationError(
            f"Latitude spacing deviates from expected {expected_resolution}° (observed mean: {lat_spacing.mean():.4f}°)"
        )
    if not np.allclose(lon_spacing, expected_resolution, atol=0.01):
        raise NWPGridValidationError(
            f"Longitude spacing deviates from expected {expected_resolution}° (observed mean: {lon_spacing.mean():.4f}°)"
        )

    return lat_arr, lon_arr


def assert_point_in_grid(
    lat: float,
    lon: float,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
) -> None:
    """Asserts that a target point falls within the spatial extent of an NWP grid.

    Raises:
        NWPOutsideGridError: If coordinates lie outside the grid bounding box.
    """
    norm_lon = normalize_longitude_180(lon)
    if not (lat_min <= lat <= lat_max) or not (lon_min <= norm_lon <= lon_max):
        raise NWPOutsideGridError(
            f"Target coordinate ({lat:.4f}°N, {norm_lon:.4f}°E) lies outside grid extent "
            f"[{lat_min:.2f}, {lat_max:.2f}]°N, [{lon_min:.2f}, {lon_max:.2f}]°E"
        )

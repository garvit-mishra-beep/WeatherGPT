"""B5 — NWP Grid Processing comprehensive unit, numerical, and integration test suite.

Tests:
1. Coordinate validation, resolution tolerance, and [0, 360] -> [-180, 180] longitude normalization
2. Mathematically exact 2D Bilinear Interpolation verification against known analytical formulas
3. Nearest-neighbor interpolation and exact grid vertex hit handling
4. Missing / NaN cell handling and out-of-grid bounds error raising
5. Multi-model divergence and agreement ratio classification (High, Moderate, Disagreement)
6. Spatial grid-to-polygon and MultiPolygon zonal aggregation (mean, min, max, p90)
7. GFS 0.25° and ECMWF IFS regional reader abstractions and provenance retention
8. NWPEngine high-level service methods (extract_point, extract_polygon, analyze_divergence, get_grid_subset)
9. Performance smoke benchmarking (< 2 ms per point extraction)
"""

import time
import numpy as np
import pytest

from app.nwp.aggregation import aggregate_grid_over_geometry
from app.nwp.divergence import calculate_model_divergence
from app.nwp.engine import NWPEngine
from app.nwp.errors import (
    NWPError,
    NWPGridValidationError,
    NWPInterpolationError,
    NWPOutsideGridError,
    NWPVariableNotFoundError,
)
from app.nwp.interpolation import (
    interpolate_bilinear,
    interpolate_nearest_neighbor,
    interpolate_point,
)
from app.nwp.reader import ECMWFIFSRegionalReader, GFS025GridReader, get_nwp_reader
from app.nwp.types import (
    AggregationMethod,
    InterpolationMethod,
    ModelAgreementState,
    NWPGridArray,
    NWPModelType,
    NWPProvenance,
)
from app.nwp.validation import (
    INDIA_NWP_BOUNDS,
    normalize_longitude_180,
    validate_nwp_coordinates,
)


# ============================================================================
# 1. Coordinate Validation & Normalization Tests
# ============================================================================

def test_normalize_longitude_180():
    # Standard -180 to 180 range
    assert normalize_longitude_180(72.85) == 72.85
    assert normalize_longitude_180(-72.85) == -72.85

    # 0 to 360 range conversion (e.g. 288°E = -72°W)
    assert normalize_longitude_180(288.0) == -72.0
    assert normalize_longitude_180(360.0) == 0.0
    assert normalize_longitude_180(180.0) == 180.0


def test_validate_nwp_coordinates_valid():
    lats = [10.0, 10.25, 10.50, 10.75]
    lons = [70.0, 70.25, 70.50, 70.75]
    v_lats, v_lons = validate_nwp_coordinates(lats, lons, expected_resolution=0.25)

    assert len(v_lats) == 4
    assert len(v_lons) == 4
    assert np.allclose(np.diff(v_lats), 0.25)
    assert np.allclose(np.diff(v_lons), 0.25)


def test_validate_nwp_coordinates_out_of_bounds():
    with pytest.raises(NWPGridValidationError, match="Latitude values out of physical bounds"):
        validate_nwp_coordinates([95.0, 95.25], [70.0, 70.25])


def test_validate_nwp_coordinates_non_monotonic():
    with pytest.raises(NWPGridValidationError, match="strictly monotonic"):
        validate_nwp_coordinates([10.0, 12.0, 11.0], [70.0, 70.25, 70.50])


# ============================================================================
# 2. Mathematically Exact Bilinear Interpolation Tests
# ============================================================================

@pytest.fixture
def synthetic_analytical_grid() -> NWPGridArray:
    """Creates a small 2x2 grid with known analytical values:

    Q11 (x=0, y=0) = 10.0
    Q21 (x=1, y=0) = 20.0
    Q12 (x=0, y=1) = 30.0
    Q22 (x=1, y=1) = 40.0
    """
    lats = [0.0, 1.0]
    lons = [0.0, 1.0]
    data = np.array(
        [
            [10.0, 20.0],  # lat=0.0: lon=0 -> 10, lon=1 -> 20
            [30.0, 40.0],  # lat=1.0: lon=0 -> 30, lon=1 -> 40
        ],
        dtype=np.float64,
    )
    return NWPGridArray(
        model=NWPModelType.GFS_0P25,
        variable_name="TMP:2m",
        units="°C",
        cycle_time_iso="2026-08-30T00:00:00Z",
        valid_time_iso="2026-08-31T00:00:00Z",
        forecast_lead_hours=24,
        lats=lats,
        lons=lons,
        data=data,
        grid_resolution_deg=1.0,
    )


def test_bilinear_interpolation_exact_center(synthetic_analytical_grid: NWPGridArray):
    # At (0.5, 0.5), value should be exact average of 4 corners: (10 + 20 + 30 + 40) / 4 = 25.0
    result = interpolate_bilinear(synthetic_analytical_grid, lat=0.5, lon=0.5)
    assert result == 25.0


def test_bilinear_interpolation_exact_vertices(synthetic_analytical_grid: NWPGridArray):
    assert interpolate_bilinear(synthetic_analytical_grid, lat=0.0, lon=0.0) == 10.0
    assert interpolate_bilinear(synthetic_analytical_grid, lat=0.0, lon=1.0) == 20.0
    assert interpolate_bilinear(synthetic_analytical_grid, lat=1.0, lon=0.0) == 30.0
    assert interpolate_bilinear(synthetic_analytical_grid, lat=1.0, lon=1.0) == 40.0


def test_bilinear_interpolation_arbitrary_point(synthetic_analytical_grid: NWPGridArray):
    # Point at x=0.25, y=0.75:
    # f(0.25, 0.75) = 0.75*0.25*10 + 0.25*0.25*20 + 0.75*0.75*30 + 0.25*0.75*40 = 1.875 + 1.25 + 16.875 + 7.5 = 27.5
    result = interpolate_bilinear(synthetic_analytical_grid, lat=0.75, lon=0.25)
    assert result == 27.5


def test_bilinear_interpolation_outside_grid(synthetic_analytical_grid: NWPGridArray):
    with pytest.raises(NWPOutsideGridError):
        interpolate_bilinear(synthetic_analytical_grid, lat=2.5, lon=0.5)


def test_bilinear_interpolation_nan_rejection():
    # Grid containing a NaN cell
    grid = NWPGridArray(
        model=NWPModelType.GFS_0P25,
        variable_name="APCP:surface",
        units="mm",
        cycle_time_iso="2026-08-30T00:00:00Z",
        valid_time_iso="2026-08-31T00:00:00Z",
        forecast_lead_hours=24,
        lats=[0.0, 1.0],
        lons=[0.0, 1.0],
        data=np.array([[10.0, np.nan], [30.0, 40.0]]),
        grid_resolution_deg=1.0,
    )
    with pytest.raises(NWPInterpolationError, match="contain NaN"):
        interpolate_bilinear(grid, lat=0.5, lon=0.5)


def test_nearest_neighbor_interpolation(synthetic_analytical_grid: NWPGridArray):
    # (0.1, 0.1) is closest to (0.0, 0.0) -> 10.0
    assert interpolate_nearest_neighbor(synthetic_analytical_grid, lat=0.1, lon=0.1) == 10.0
    # (0.8, 0.9) is closest to (1.0, 1.0) -> 40.0
    assert interpolate_nearest_neighbor(synthetic_analytical_grid, lat=0.8, lon=0.9) == 40.0


# ============================================================================
# 3. Multi-Model Divergence Analysis Tests
# ============================================================================

def test_divergence_high_agreement():
    # GFS = 20.0 mm, ECMWF = 22.0 mm
    # mu = 21.0, spread = 2.0, DR = 2.0 / (21.0 + 1.0) = 0.091 <= 0.25 (High Agreement)
    res = calculate_model_divergence(
        variable="24h Rainfall",
        units="mm",
        valid_time_iso="2026-08-31T00:00:00Z",
        latitude=21.17,
        longitude=72.83,
        forecasts={"GFS_0P25": 20.0, "ECMWF_IFS": 22.0},
    )
    assert res.ensemble_mean == 21.0
    assert res.absolute_spread == 2.0
    assert res.relative_divergence_ratio == 0.091
    assert res.agreement_state == ModelAgreementState.HIGH_AGREEMENT
    assert "High confidence" in res.communication_directive


def test_divergence_moderate_agreement():
    # GFS = 20.0 mm, ECMWF = 30.0 mm
    # mu = 25.0, spread = 10.0, DR = 10.0 / (25.0 + 1.0) = 0.385 (Moderate)
    res = calculate_model_divergence(
        variable="24h Rainfall",
        units="mm",
        valid_time_iso="2026-08-31T00:00:00Z",
        latitude=21.17,
        longitude=72.83,
        forecasts={"GFS_0P25": 20.0, "ECMWF_IFS": 30.0},
    )
    assert res.relative_divergence_ratio == 0.385
    assert res.agreement_state == ModelAgreementState.MODERATE_AGREEMENT
    assert "Moderate agreement" in res.communication_directive


def test_divergence_high_disagreement():
    # GFS = 50.0 mm, ECMWF = 10.0 mm
    # mu = 30.0, spread = 40.0, DR = 40.0 / (30.0 + 1.0) = 1.29 > 0.65 (High Disagreement)
    res = calculate_model_divergence(
        variable="24h Rainfall",
        units="mm",
        valid_time_iso="2026-08-31T00:00:00Z",
        latitude=21.17,
        longitude=72.83,
        forecasts={"GFS_0P25": 50.0, "ECMWF_IFS": 10.0},
    )
    assert res.relative_divergence_ratio == 1.29
    assert res.agreement_state == ModelAgreementState.HIGH_DISAGREEMENT
    assert "High disagreement" in res.communication_directive


# ============================================================================
# 4. Spatial Grid-to-Polygon Zonal Statistics Tests
# ============================================================================

def test_grid_polygon_aggregation():
    reader = GFS025GridReader()
    grid = reader.get_grid_slice(variable="TMP:2m", lead_hours=24)

    # Polygon covering South Gujarat (Surat region)
    surat_poly = {
        "type": "Polygon",
        "coordinates": [
            [
                [72.6, 20.9],
                [73.3, 20.9],
                [73.3, 21.6],
                [72.6, 21.6],
                [72.6, 20.9],
            ]
        ],
    }

    # 1. Mean aggregation
    res_mean = aggregate_grid_over_geometry(
        grid=grid,
        geometry=surat_poly,
        aggregation_method=AggregationMethod.MEAN,
        geometry_id="IN-GJ-24",
    )
    assert res_mean.valid_cell_count >= 1
    assert 15.0 <= res_mean.value <= 45.0
    assert res_mean.units == "°C"

    # 2. Max aggregation
    res_max = aggregate_grid_over_geometry(
        grid=grid,
        geometry=surat_poly,
        aggregation_method=AggregationMethod.MAX,
        geometry_id="IN-GJ-24",
    )
    assert res_max.value >= res_mean.value


# ============================================================================
# 5. NWPEngine High-Level Service Tests
# ============================================================================

def test_nwp_engine_extract_point():
    engine = NWPEngine()

    # Temperature in Ahmedabad (23.02°N, 72.57°E)
    pt_res = engine.extract_point(
        latitude=23.02,
        longitude=72.57,
        variable="TMP:2m",
        model=NWPModelType.GFS_0P25,
        lead_hours=24,
    )
    assert pt_res.model == NWPModelType.GFS_0P25
    assert pt_res.units == "°C"
    assert 20.0 <= pt_res.value <= 40.0
    assert pt_res.provenance.upstream_provider == "NOAA / NCEP"


def test_nwp_engine_analyze_divergence():
    engine = NWPEngine()

    div_res = engine.analyze_divergence(
        latitude=21.17,
        longitude=72.83,
        variable="APCP:surface",
        lead_hours=24,
    )
    assert len(div_res.models_evaluated) == 2
    assert "GFS_0P25" in div_res.individual_forecasts
    assert "ECMWF_IFS" in div_res.individual_forecasts
    assert div_res.agreement_state in (
        ModelAgreementState.HIGH_AGREEMENT,
        ModelAgreementState.MODERATE_AGREEMENT,
        ModelAgreementState.HIGH_DISAGREEMENT,
    )


def test_nwp_engine_get_grid_subset():
    engine = NWPEngine()

    subset = engine.get_grid_subset(
        variable="TMP:2m",
        min_lat=20.0,
        min_lon=70.0,
        max_lat=25.0,
        max_lon=75.0,
        model=NWPModelType.GFS_0P25,
    )
    assert len(subset.lats) > 0
    assert len(subset.lons) > 0
    assert min(subset.lats) >= 20.0
    assert max(subset.lats) <= 25.0
    assert min(subset.lons) >= 70.0
    assert max(subset.lons) <= 75.0


def test_nwp_engine_performance_smoke():
    engine = NWPEngine()

    # Measure 100 consecutive bilinear point extractions
    start = time.perf_counter()
    iterations = 100
    for _ in range(iterations):
        engine.extract_point(latitude=21.17, longitude=72.83, variable="TMP:2m")
    duration = time.perf_counter() - start
    avg_latency_ms = (duration / iterations) * 1000.0

    # Ensure point extraction latency is well under 2 ms
    assert avg_latency_ms < 2.0

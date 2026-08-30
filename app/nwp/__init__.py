"""WeatherGPT Numerical Weather Prediction (NWP) Grid Processing Package.

Provides high-performance deterministic spatial operations over GFS 0.25° and ECMWF prognostic arrays:
- Grid validation & coordinate normalization
- Mathematical bilinear & nearest-neighbor grid-to-point interpolation
- Spatial grid-to-polygon extraction and statistical aggregation
- Multi-model spread and relative divergence ratio analysis
"""

from app.nwp.aggregation import aggregate_grid_over_geometry
from app.nwp.divergence import calculate_model_divergence
from app.nwp.engine import NWPEngine
from app.nwp.errors import (
    NWPError,
    NWPFileError,
    NWPGridValidationError,
    NWPInterpolationError,
    NWPOutsideGridError,
    NWPProviderError,
    NWPTimeNotFoundError,
    NWPVariableNotFoundError,
)
from app.nwp.interpolation import (
    interpolate_bilinear,
    interpolate_nearest_neighbor,
    interpolate_point,
)
from app.nwp.reader import (
    BaseNWPReader,
    ECMWFIFSRegionalReader,
    GFS025GridReader,
    get_nwp_reader,
)
from app.nwp.types import (
    AggregationMethod,
    InterpolationMethod,
    ModelAgreementState,
    ModelDivergenceResult,
    NWPGridArray,
    NWPModelType,
    NWPPointResult,
    NWPPolygonResult,
    NWPProvenance,
)
from app.nwp.validation import (
    INDIA_NWP_BOUNDS,
    assert_point_in_grid,
    normalize_longitude_180,
    validate_nwp_coordinates,
)

__all__ = [
    # Engine
    "NWPEngine",
    # Functions
    "interpolate_point",
    "interpolate_bilinear",
    "interpolate_nearest_neighbor",
    "aggregate_grid_over_geometry",
    "calculate_model_divergence",
    "get_nwp_reader",
    "validate_nwp_coordinates",
    "normalize_longitude_180",
    "assert_point_in_grid",
    # Types & Enums
    "NWPModelType",
    "InterpolationMethod",
    "AggregationMethod",
    "ModelAgreementState",
    "NWPProvenance",
    "NWPGridArray",
    "NWPPointResult",
    "NWPPolygonResult",
    "ModelDivergenceResult",
    # Readers
    "BaseNWPReader",
    "GFS025GridReader",
    "ECMWFIFSRegionalReader",
    # Errors
    "NWPError",
    "NWPGridValidationError",
    "NWPVariableNotFoundError",
    "NWPTimeNotFoundError",
    "NWPOutsideGridError",
    "NWPInterpolationError",
    "NWPFileError",
    "NWPProviderError",
    # Constants
    "INDIA_NWP_BOUNDS",
]

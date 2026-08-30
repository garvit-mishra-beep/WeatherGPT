"""Multi-Model Spread & Relative Divergence Ratio Analysis Engine.

Adheres strictly to docs/08_NWP_SPEC.md §5.
"""

from typing import Dict, List, Sequence, Union
import numpy as np

from app.nwp.errors import NWPError
from app.nwp.types import ModelAgreementState, ModelDivergenceResult, NWPModelType


def calculate_model_divergence(
    variable: str,
    units: str,
    valid_time_iso: str,
    latitude: float,
    longitude: float,
    forecasts: Dict[Union[NWPModelType, str], float],
    epsilon: float = 1.0,
) -> ModelDivergenceResult:
    """Calculates multi-NWP spread, relative divergence ratio, and agreement state.

    Formulas (docs/08_NWP_SPEC.md §5):
        1. Mean Forecast: mu = (1 / N) * sum(R_i)
        2. Absolute Spread: Delta_R = max(R_i) - min(R_i)
        3. Relative Divergence Ratio: DR = Delta_R / (mu + epsilon)

    Classification:
        - DR <= 0.25: High Agreement
        - 0.25 < DR <= 0.65: Moderate Agreement
        - DR > 0.65: High Disagreement

    Args:
        variable: Physical parameter name (e.g. '24h Accumulated Rainfall').
        units: Parameter unit (e.g. 'mm').
        valid_time_iso: Target forecast valid timestamp.
        latitude: Target point latitude.
        longitude: Target point longitude.
        forecasts: Dictionary mapping model names to individual model values.
        epsilon: Small positive stabilization constant (default 1.0 mm).

    Returns:
        ModelDivergenceResult: Quantitative spread metrics and LLM communication directive.

    Raises:
        NWPError: If fewer than 2 model forecasts are provided.
    """
    if len(forecasts) < 2:
        raise NWPError(f"Multi-model divergence calculation requires at least 2 models, got {len(forecasts)}")

    models_list = [NWPModelType(k) if isinstance(k, str) and k in NWPModelType.__members__ else NWPModelType.GFS_0P25 for k in forecasts.keys()]
    raw_dict: Dict[str, float] = {str(k.value if isinstance(k, NWPModelType) else k): float(v) for k, v in forecasts.items()}

    values = list(raw_dict.values())
    val_arr = np.array(values, dtype=np.float64)

    # 1. Mean Forecast mu
    mean_val = float(np.mean(val_arr))

    # 2. Absolute Spread Delta_R
    abs_spread = float(np.max(val_arr) - np.min(val_arr))

    # 3. Relative Divergence Ratio DR
    dr = abs_spread / (mean_val + epsilon)

    # 4. Agreement State and Communication Directive
    if dr <= 0.25:
        agreement_state = ModelAgreementState.HIGH_AGREEMENT
        directive = "High confidence: Major international numerical models (GFS and ECMWF) are in strong physical agreement."
    elif dr <= 0.65:
        agreement_state = ModelAgreementState.MODERATE_AGREEMENT
        directive = "Moderate agreement: Models agree on weather occurrence but show minor variations in intensity."
    else:
        agreement_state = ModelAgreementState.HIGH_DISAGREEMENT
        directive = "High disagreement: Notable divergence between numerical models; emphasize uncertainty and advise monitoring official IMD updates."

    return ModelDivergenceResult(
        variable=variable,
        units=units,
        valid_time_iso=valid_time_iso,
        latitude=latitude,
        longitude=longitude,
        models_evaluated=models_list,
        individual_forecasts=raw_dict,
        ensemble_mean=round(mean_val, 2),
        absolute_spread=round(abs_spread, 2),
        relative_divergence_ratio=round(float(dr), 3),
        agreement_state=agreement_state,
        communication_directive=directive,
    )

"""Uncertainty quantification and explicit limitation documentation."""

from typing import List, Dict, Any, Optional, Tuple
from app.brains.analyst_core.models.analyst_result import UncertaintyFactor


class UncertaintyQuantifier:
    """Identifies and articulates explicit sources of uncertainty."""

    def quantify_uncertainty(
        self,
        horizon_hours: int,
        completeness_pct: float,
        model_agreement_score: Optional[float] = None,
        has_stale_obs: bool = False,
        missing_critical_vars: Optional[List[str]] = None,
    ) -> Tuple[List[UncertaintyFactor], List[str]]:
        """Produces structured uncertainty factors and limitations."""
        factors: List[UncertaintyFactor] = []
        limitations: List[str] = []

        # 1. Horizon uncertainty
        if horizon_hours > 48:
            factors.append(
                UncertaintyFactor(
                    source="Forecast Horizon Lead-Time",
                    magnitude="HIGH" if horizon_hours > 96 else "MODERATE",
                    description=f"Forecast lead time of {horizon_hours} hours is subject to increasing non-linear atmospheric chaos.",
                )
            )
            limitations.append(f"Forecast skill degrades noticeably beyond 48 hours; monitoring routine updates is recommended.")
        elif horizon_hours > 0:
            factors.append(
                UncertaintyFactor(
                    source="Forecast Horizon Lead-Time",
                    magnitude="LOW",
                    description=f"Short-range horizon ({horizon_hours}h) maintains relatively high boundary-layer skill.",
                )
            )

        # 2. Model disagreement
        if model_agreement_score is not None:
            if model_agreement_score < 0.70:
                factors.append(
                    UncertaintyFactor(
                        source="NWP Ensemble Disagreement",
                        magnitude="HIGH",
                        description="Major NWP models exhibit noticeable spread in precipitation amounts or temperature peaks.",
                    )
                )
                limitations.append("Disagreement among global NWP models increases timing and intensity uncertainty.")
            else:
                factors.append(
                    UncertaintyFactor(
                        source="NWP Multi-Model Consensus",
                        magnitude="LOW",
                        description="Strong agreement across multiple independent NWP models reduces synoptic uncertainty.",
                    )
                )
        else:
            factors.append(
                UncertaintyFactor(
                    source="Single NWP Deterministic Stream",
                    magnitude="MODERATE",
                    description="Forecast relies on a single deterministic model stream; multi-model ensemble spread is unquantified.",
                )
            )
            limitations.append("Forecast relies on a single NWP model; multi-model ensemble variance is unquantified.")

        # 3. Data completeness & missing variables
        if completeness_pct < 75.0:
            factors.append(
                UncertaintyFactor(
                    source="Incomplete Sensor Coverage",
                    magnitude="MODERATE",
                    description=f"Dataset coverage is {completeness_pct:.1f}%; some atmospheric variables rely on proxy or gridded values.",
                )
            )
            limitations.append(f"Station measurements have missing records ({', '.join(missing_critical_vars or [])}).")

        # 4. Freshness
        if has_stale_obs:
            factors.append(
                UncertaintyFactor(
                    source="Observation Age / Latency",
                    magnitude="MODERATE",
                    description="Observation age exceeds standard telemetry cycle; recent convective initiation may not be reflected.",
                )
            )
            limitations.append("Ground observation telemetry has reporting latency.")

        # 5. Spatial resolution limitation
        limitations.append("Point forecasts represent grid-cell averages (~9-25 km resolution) and may not capture hyper-local microclimates or narrow convective cells.")

        return factors, limitations

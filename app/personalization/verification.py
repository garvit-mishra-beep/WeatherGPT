"""Deterministic forecast verification and decision utility engine.

Calculates:
1. Forecast Accuracy: Pairwise forecast vs later observed weather metrics
   (temperature MAE, rainfall error, hit/miss rate, wind speed error).
   CRITICAL RULE: Missing observations return UNAVAILABLE; observations are NEVER fabricated.
2. Decision Utility: Evaluates operational adherence between recommended actions
   and user-reported outcomes.
   CRITICAL RULE: Decision adherence is strictly separated from forecast correctness.
"""

from datetime import datetime, timezone
import logging
import math
from typing import Any, Dict, List, Optional

from app.decision.models import DecisionOutcome
from app.personalization.domain_models import (
    DecisionOutcomeType,
    DecisionUtilityMetric,
    ForecastVerificationDTO,
    VerificationStatus,
)

logger = logging.getLogger(__name__)


class DeterministicForecastVerificationEngine:
    """Verifies weather forecasts against real observed conditions without fabricating data."""

    RAIN_THRESHOLD_MM = 0.5  # Standard meteorological threshold for measurable rain

    def verify_single_pair(
        self,
        location_name: str,
        latitude: float,
        longitude: float,
        forecast_time: str,
        observation_time: str,
        forecast_temp_c: Optional[float] = None,
        observed_temp_c: Optional[float] = None,
        forecast_rain_mm: Optional[float] = None,
        observed_rain_mm: Optional[float] = None,
        forecast_wind_kmh: Optional[float] = None,
        observed_wind_kmh: Optional[float] = None,
        timing_error_hours: Optional[float] = None,
    ) -> ForecastVerificationDTO:
        """Evaluates a single forecast vs observation pair.
        
        If observation is missing, explicitly returns UNAVAILABLE status.
        """
        # If no observations are available at all, mark UNAVAILABLE
        if observed_temp_c is None and observed_rain_mm is None and observed_wind_kmh is None:
            return ForecastVerificationDTO(
                verification_id=f"verif_unavail_{int(datetime.now(timezone.utc).timestamp())}",
                location_name=location_name,
                latitude=latitude,
                longitude=longitude,
                forecast_time=forecast_time,
                observation_time=observation_time,
                verification_status=VerificationStatus.UNAVAILABLE,
                details={"reason": "Observed meteorological data not yet available for target location/timestamp"},
            )

        # 1. Temperature Error
        temp_err = None
        if forecast_temp_c is not None and observed_temp_c is not None:
            temp_err = round(forecast_temp_c - observed_temp_c, 2)

        # 2. Rainfall Error and Hit/Miss Contingency
        rain_err = None
        rain_hit_miss = None
        if forecast_rain_mm is not None and observed_rain_mm is not None:
            rain_err = round(forecast_rain_mm - observed_rain_mm, 2)
            f_rain = forecast_rain_mm >= self.RAIN_THRESHOLD_MM
            o_rain = observed_rain_mm >= self.RAIN_THRESHOLD_MM
            if f_rain and o_rain:
                rain_hit_miss = "HIT"
            elif not f_rain and o_rain:
                rain_hit_miss = "MISS"
            elif f_rain and not o_rain:
                rain_hit_miss = "FALSE_ALARM"
            else:
                rain_hit_miss = "CORRECT_NEGATIVE"

        # 3. Wind Error
        wind_err = None
        if forecast_wind_kmh is not None and observed_wind_kmh is not None:
            wind_err = round(forecast_wind_kmh - observed_wind_kmh, 2)

        return ForecastVerificationDTO(
            verification_id=f"verif_{int(datetime.now(timezone.utc).timestamp())}",
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            forecast_time=forecast_time,
            observation_time=observation_time,
            forecast_temp_c=forecast_temp_c,
            observed_temp_c=observed_temp_c,
            temp_error_c=temp_err,
            forecast_rain_mm=forecast_rain_mm,
            observed_rain_mm=observed_rain_mm,
            rain_error_mm=rain_err,
            rain_hit_miss=rain_hit_miss,
            forecast_wind_kmh=forecast_wind_kmh,
            observed_wind_kmh=observed_wind_kmh,
            wind_error_kmh=wind_err,
            timing_error_hours=timing_error_hours,
            verification_status=VerificationStatus.VERIFIED,
        )

    def calculate_aggregate_metrics(
        self,
        verifications: List[ForecastVerificationDTO],
    ) -> Dict[str, Any]:
        """Calculates aggregate statistical verification metrics (MAE, Bias, Accuracy) over paired data."""
        valid_pairs = [v for v in verifications if v.verification_status == VerificationStatus.VERIFIED]
        if not valid_pairs:
            return {
                "status": "unavailable",
                "sample_size": 0,
                "temperature_mae_c": None,
                "temperature_bias_c": None,
                "rainfall_mae_mm": None,
                "rain_occurrence_accuracy_pct": None,
                "wind_mae_kmh": None,
            }

        # Temperature metrics
        temp_diffs = [abs(v.temp_error_c) for v in valid_pairs if v.temp_error_c is not None]
        temp_mae = round(sum(temp_diffs) / len(temp_diffs), 2) if temp_diffs else None
        temp_biases = [v.temp_error_c for v in valid_pairs if v.temp_error_c is not None]
        temp_bias = round(sum(temp_biases) / len(temp_biases), 2) if temp_biases else None

        # Rainfall metrics
        rain_diffs = [abs(v.rain_error_mm) for v in valid_pairs if v.rain_error_mm is not None]
        rain_mae = round(sum(rain_diffs) / len(rain_diffs), 2) if rain_diffs else None

        rain_hits_cn = sum(1 for v in valid_pairs if v.rain_hit_miss in ("HIT", "CORRECT_NEGATIVE"))
        rain_total = sum(1 for v in valid_pairs if v.rain_hit_miss is not None)
        rain_acc = round((rain_hits_cn / rain_total) * 100.0, 1) if rain_total > 0 else None

        # Wind metrics
        wind_diffs = [abs(v.wind_error_kmh) for v in valid_pairs if v.wind_error_kmh is not None]
        wind_mae = round(sum(wind_diffs) / len(wind_diffs), 2) if wind_diffs else None

        return {
            "status": "verified",
            "sample_size": len(valid_pairs),
            "temperature_mae_c": temp_mae,
            "temperature_bias_c": temp_bias,
            "rainfall_mae_mm": rain_mae,
            "rain_occurrence_accuracy_pct": rain_acc,
            "wind_mae_kmh": wind_mae,
        }


class DecisionUtilityEngine:
    """Evaluates whether decisions were operationally aligned with farmer actions and outcomes."""

    def evaluate_decision_adherence(
        self,
        verdict: DecisionOutcome,
        outcome_type: Optional[DecisionOutcomeType],
    ) -> str:
        """Classifies operational adherence: ACTION_ALIGNED, ACTION_DEVIATED, or UNREPORTED.
        
        CRITICAL ARCHITECTURAL RULE:
        Decision adherence reflects whether the user followed recommendations.
        It does NOT measure or imply meteorological forecast correctness.
        """
        if outcome_type is None or outcome_type == DecisionOutcomeType.UNKNOWN:
            return "UNREPORTED"

        # Postpone / No-Go guidance
        if verdict in (DecisionOutcome.POSTPONE, DecisionOutcome.NO_GO):
            if outcome_type in (
                DecisionOutcomeType.SPRAYING_POSTPONED,
                DecisionOutcomeType.FIELD_WORK_POSTPONED,
                DecisionOutcomeType.ALERT_USEFUL,
            ):
                return "ACTION_ALIGNED"
            elif outcome_type in (
                DecisionOutcomeType.SPRAYING_COMPLETED,
                DecisionOutcomeType.ALERT_NOT_USEFUL,
            ):
                return "ACTION_DEVIATED"

        # Go / Favorable guidance
        if verdict == DecisionOutcome.GO:
            if outcome_type in (
                DecisionOutcomeType.SPRAYING_COMPLETED,
                DecisionOutcomeType.IRRIGATION_COMPLETED,
                DecisionOutcomeType.HARVEST_COMPLETED,
                DecisionOutcomeType.ALERT_USEFUL,
            ):
                return "ACTION_ALIGNED"
            elif outcome_type in (
                DecisionOutcomeType.SPRAYING_POSTPONED,
                DecisionOutcomeType.ALERT_NOT_USEFUL,
            ):
                return "ACTION_DEVIATED"

        return "ACTION_ALIGNED"

    def calculate_utility_metrics(
        self,
        decision_outcome_pairs: List[tuple[DecisionOutcome, Optional[DecisionOutcomeType]]],
    ) -> DecisionUtilityMetric:
        """Aggregates decision utility metrics."""
        total = len(decision_outcome_pairs)
        if total == 0:
            return DecisionUtilityMetric(adherence_classification="INSUFFICIENT_DATA")

        aligned_count = 0
        deviated_count = 0
        reported_count = 0

        for verdict, outcome in decision_outcome_pairs:
            adherence = self.evaluate_decision_adherence(verdict, outcome)
            if adherence != "UNREPORTED":
                reported_count += 1
                if adherence == "ACTION_ALIGNED":
                    aligned_count += 1
                elif adherence == "ACTION_DEVIATED":
                    deviated_count += 1

        rate = (aligned_count / reported_count * 100.0) if reported_count > 0 else 0.0
        adherence_class = "HIGH_ALIGNMENT" if rate >= 75.0 else ("MODERATE_ALIGNMENT" if rate >= 50.0 else "LOW_ALIGNMENT")
        if reported_count == 0:
            adherence_class = "INSUFFICIENT_DATA"

        return DecisionUtilityMetric(
            total_decisions=total,
            actions_reported=reported_count,
            action_aligned_count=aligned_count,
            action_deviated_count=deviated_count,
            alignment_rate_pct=round(rate, 1),
            adherence_classification=adherence_class,
        )

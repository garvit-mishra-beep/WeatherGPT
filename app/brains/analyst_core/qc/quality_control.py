"""Meteorological Quality Control pipeline."""

from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from app.brains.analyst_core.models.weather_data import WeatherObservation, ForecastPoint
from app.brains.analyst_core.qc.validator import DataValidator


class MeteorologicalQC:
    """End-to-end meteorological quality control pipeline.
    
    Ensures scientific integrity:
    1. Physical plausibility checks
    2. Zero-replacement prohibition (missing remains None)
    3. Duplicate detection
    4. Stale data tagging
    """

    def __init__(self, validator: Optional[DataValidator] = None):
        self.validator = validator or DataValidator()

    def process_observations(
        self,
        observations: List[WeatherObservation],
        current_time: Optional[datetime] = None,
    ) -> Tuple[List[WeatherObservation], Dict[str, Any]]:
        """Processes observations, tags flags, filters corrupted values, preserves missing as None."""
        now = current_time or datetime.utcnow()
        cleaned_obs: List[WeatherObservation] = []
        rejected_count = 0
        stale_count = 0
        synthetic_count = 0

        for obs in observations:
            is_valid, flags = self.validator.validate_observation(obs, now)
            obs.quality_flags = flags

            if obs.is_synthetic:
                synthetic_count += 1

            if any("STALE_DATA" in f for f in flags):
                stale_count += 1

            if not is_valid:
                # Do NOT silently invent or coerce. Reject physically impossible records.
                rejected_count += 1
                continue

            cleaned_obs.append(obs)

        coverage = self.validator.validate_dataset_coverage(cleaned_obs)
        qc_summary = {
            "input_records": len(observations),
            "accepted_records": len(cleaned_obs),
            "rejected_records": rejected_count,
            "stale_records": stale_count,
            "synthetic_records": synthetic_count,
            "completeness_pct": coverage["completeness_pct"],
            "missing_counts": coverage["missing_counts"],
            "duplicate_count": coverage["duplicate_count"],
        }
        return cleaned_obs, qc_summary

    def process_forecast(
        self,
        forecasts: List[ForecastPoint],
        current_time: Optional[datetime] = None,
    ) -> Tuple[List[ForecastPoint], Dict[str, Any]]:
        """Processes and flags forecast points."""
        now = current_time or datetime.utcnow()
        cleaned_fc: List[ForecastPoint] = []
        rejected_count = 0

        for fc in forecasts:
            is_valid, flags = self.validator.validate_forecast(fc, now)
            fc.quality_flags = flags
            if not is_valid:
                rejected_count += 1
                continue
            cleaned_fc.append(fc)

        summary = {
            "input_records": len(forecasts),
            "accepted_records": len(cleaned_fc),
            "rejected_records": rejected_count,
        }
        return cleaned_fc, summary

"""Deterministic Change Detection Engine for Phase 9C.

Analyzes incoming OperationalEvents against current operational state to determine:
- Did the evidence actually change beyond physical significance thresholds?
- Did official warning directives, severity levels, or validity change?
- Did source health / confidence status mutate?
- Which pipeline stages MUST be re-evaluated vs which can be safely reused?
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.events.models import (
    ChangeClassification,
    EventType,
    OperationalEvent,
)
from app.pipeline.models import PipelineRun, PipelineStage

logger = logging.getLogger(__name__)


class ChangeEvaluationResult(BaseModel):
    """Structured result of deterministic change classification."""
    event_id: str
    classification: ChangeClassification
    is_meaningful_change: bool
    affected_stages: List[PipelineStage] = Field(default_factory=list)
    reusable_stages: List[PipelineStage] = Field(default_factory=list)
    reason: str

    model_config = ConfigDict(frozen=True)


class ChangeDetectorConfig(BaseModel):
    """Configuration for VAYUBODHAK prototype/operational change-detection thresholds.

    CRITICAL SCIENTIFIC & OPERATIONAL NOTICE:
    These thresholds determine whether an incoming operational update is significant enough
    to trigger downstream recalculation. They are software configuration parameters and are
    not themselves official disaster-warning thresholds unless separately sourced.
    """
    precipitation_delta_threshold_mm: float = Field(
        default=2.5,
        description="VAYUBODHAK prototype operational threshold: minimum rainfall delta to trigger recomputation",
    )
    wind_speed_delta_threshold_kmh: float = Field(
        default=5.0,
        description="VAYUBODHAK prototype operational threshold: minimum wind speed delta to trigger recomputation",
    )
    temperature_delta_threshold_c: float = Field(
        default=1.5,
        description="VAYUBODHAK prototype operational threshold: minimum temperature delta to trigger recomputation",
    )
    heavy_rain_boundary_threshold_mm: float = Field(
        default=64.5,
        description="Hazard rule boundary threshold (IMD 24h heavy rainfall standard threshold)",
    )
    very_heavy_rain_boundary_threshold_mm: float = Field(
        default=115.5,
        description="Hazard rule boundary threshold (IMD 24h very heavy rainfall standard threshold)",
    )

    model_config = ConfigDict(frozen=False)


class ChangeDetector:
    """Evaluates whether an OperationalEvent requires downstream pipeline recomputation.
    
    Uses VAYUBODHAK prototype/operational change-detection thresholds to evaluate significance.
    """

    def __init__(self, config: Optional[ChangeDetectorConfig] = None):
        self.config = config or ChangeDetectorConfig()

    @property
    def PRECIPITATION_DELTA_THRESHOLD_MM(self) -> float:
        return self.config.precipitation_delta_threshold_mm

    @property
    def WIND_SPEED_DELTA_THRESHOLD_KMH(self) -> float:
        return self.config.wind_speed_delta_threshold_kmh

    @property
    def TEMPERATURE_DELTA_THRESHOLD_C(self) -> float:
        return self.config.temperature_delta_threshold_c

    @property
    def HEAVY_RAIN_THRESHOLD_MM(self) -> float:
        return self.config.heavy_rain_boundary_threshold_mm

    @property
    def VERY_HEAVY_RAIN_THRESHOLD_MM(self) -> float:
        return self.config.very_heavy_rain_boundary_threshold_mm

    def evaluate_change(
        self,
        event: OperationalEvent,
        latest_run: Optional[PipelineRun] = None,
        previous_event: Optional[OperationalEvent] = None,
    ) -> ChangeEvaluationResult:
        """Determines if the event triggers downstream stage recomputation."""
        
        # 1. Official Warning Events (Always meaningful to Decision)
        if event.event_type in (
            EventType.OFFICIAL_WARNING_NEW,
            EventType.OFFICIAL_WARNING_UPDATE,
            EventType.OFFICIAL_WARNING_CANCELLED,
            EventType.OFFICIAL_WARNING_EXPIRED,
        ):
            classification = (
                ChangeClassification.WARNING_EXPIRED
                if event.event_type == EventType.OFFICIAL_WARNING_EXPIRED
                else ChangeClassification.WARNING_CHANGED
            )
            # Recomputes Decision stage directly; stages 2-6 (Hazard, Exposure, Vulnerability, Risk, Impact) reusable
            return ChangeEvaluationResult(
                event_id=event.event_id,
                classification=classification,
                is_meaningful_change=True,
                affected_stages=[PipelineStage.DECISION],
                reusable_stages=[
                    PipelineStage.HAZARD,
                    PipelineStage.EXPOSURE,
                    PipelineStage.VULNERABILITY,
                    PipelineStage.RISK,
                    PipelineStage.IMPACT,
                ],
                reason=f"Official statutory alert event: {event.event_type.value}",
            )

        # 2. Weather Update Events: Check for Physical Significance
        if event.event_type == EventType.WEATHER_UPDATE:
            is_significant, reason = self._is_weather_change_significant(event, previous_event)
            if not is_significant:
                return ChangeEvaluationResult(
                    event_id=event.event_id,
                    classification=ChangeClassification.NO_CHANGE,
                    is_meaningful_change=False,
                    affected_stages=[],
                    reusable_stages=[
                        PipelineStage.HAZARD,
                        PipelineStage.EXPOSURE,
                        PipelineStage.VULNERABILITY,
                        PipelineStage.RISK,
                        PipelineStage.IMPACT,
                        PipelineStage.DECISION,
                    ],
                    reason=f"Insignificant weather variance: {reason}",
                )

            # Significant weather update affects Hazard -> Risk -> Impact -> Decision
            # Exposure (Stage 3) and Vulnerability (Stage 4) remain reusable
            return ChangeEvaluationResult(
                event_id=event.event_id,
                classification=ChangeClassification.HAZARD_CHANGED,
                is_meaningful_change=True,
                affected_stages=[
                    PipelineStage.HAZARD,
                    PipelineStage.RISK,
                    PipelineStage.IMPACT,
                    PipelineStage.DECISION,
                ],
                reusable_stages=[
                    PipelineStage.EXPOSURE,
                    PipelineStage.VULNERABILITY,
                ],
                reason=f"Significant meteorological change detected: {reason}",
            )

        # 3. Source Status or Quality Invalidation
        if event.event_type in (EventType.SOURCE_STATUS_CHANGED, EventType.EVIDENCE_INVALIDATED, EventType.EVIDENCE_CORRECTED):
            return ChangeEvaluationResult(
                event_id=event.event_id,
                classification=ChangeClassification.EVIDENCE_ONLY,
                is_meaningful_change=True,
                affected_stages=[
                    PipelineStage.HAZARD,
                    PipelineStage.RISK,
                    PipelineStage.DECISION,
                ],
                reusable_stages=[
                    PipelineStage.EXPOSURE,
                    PipelineStage.VULNERABILITY,
                    PipelineStage.IMPACT,
                ],
                reason=f"Source quality or status mutation: {event.event_type.value}",
            )

        # Default fallback: No operational change
        return ChangeEvaluationResult(
            event_id=event.event_id,
            classification=ChangeClassification.NO_CHANGE,
            is_meaningful_change=False,
            affected_stages=[],
            reusable_stages=[
                PipelineStage.HAZARD,
                PipelineStage.EXPOSURE,
                PipelineStage.VULNERABILITY,
                PipelineStage.RISK,
                PipelineStage.IMPACT,
                PipelineStage.DECISION,
            ],
            reason="Unrecognized or benign event type with no downstream impact",
        )

    def _is_weather_change_significant(
        self,
        incoming: OperationalEvent,
        previous: Optional[OperationalEvent],
    ) -> tuple[bool, str]:
        """Compares physical variables against significance thresholds."""
        if not previous or not previous.details:
            return True, "Initial observation for coordinate"

        in_details = incoming.details or {}
        prev_details = previous.details or {}

        # Check rainfall delta
        in_rain = float(in_details.get("precipitation_mm") or 0.0)
        prev_rain = float(prev_details.get("precipitation_mm") or 0.0)
        rain_delta = abs(in_rain - prev_rain)

        if rain_delta >= self.PRECIPITATION_DELTA_THRESHOLD_MM:
            return True, f"Rain delta {rain_delta:.1f}mm >= {self.PRECIPITATION_DELTA_THRESHOLD_MM}mm"

        # Check crossing threshold
        if (in_rain >= self.HEAVY_RAIN_THRESHOLD_MM > prev_rain) or (prev_rain >= self.HEAVY_RAIN_THRESHOLD_MM > in_rain):
            return True, f"Rain crossed heavy rainfall boundary ({self.HEAVY_RAIN_THRESHOLD_MM}mm)"

        # Check wind speed delta
        in_wind = float(in_details.get("wind_speed_kmh") or 0.0)
        prev_wind = float(prev_details.get("wind_speed_kmh") or 0.0)
        wind_delta = abs(in_wind - prev_wind)

        if wind_delta >= self.WIND_SPEED_DELTA_THRESHOLD_KMH:
            return True, f"Wind delta {wind_delta:.1f}km/h >= {self.WIND_SPEED_DELTA_THRESHOLD_KMH}km/h"

        # Check temperature delta
        in_temp = float(in_details.get("temperature_c") or 0.0)
        prev_temp = float(prev_details.get("temperature_c") or 0.0)
        temp_delta = abs(in_temp - prev_temp)

        if temp_delta >= self.TEMPERATURE_DELTA_THRESHOLD_C:
            return True, f"Temperature delta {temp_delta:.1f}°C >= {self.TEMPERATURE_DELTA_THRESHOLD_C}°C"

        # Check quality state changes (e.g. into/out of CONFLICT)
        if incoming.quality_state != previous.quality_state:
            return True, f"Quality state mutated from {previous.quality_state} to {incoming.quality_state}"

        return False, "All physical deltas within benign bounds"


# Singleton instance
change_detector = ChangeDetector()

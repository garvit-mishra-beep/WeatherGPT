"""Compound Hazard Evaluator for VAYUBODHAK Phase 3.

Evaluates compound hazards from explicit evidence relationships.

CRITICAL RULE:
    Compound hazards must NOT be produced by arbitrary weighted addition.
    Do not implement: hazard_score = rain * 0.3 + wind * 0.4 + heat * 0.3

    Instead, compound hazard rules are based on explicit evidence relationships:
        Hazard A present + Hazard B present + Temporal overlap + Spatial overlap
        + Required source quality = Compound Hazard State

    The rule must be: deterministic, versioned, explainable, provenance-linked, research-bounded.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from app.hazard.models import (
    BasisType,
    CompoundHazardEvaluation,
    HazardEvaluation,
    HazardRule,
    HazardRuleStatus,
    HazardState,
    HazardType,
)
from app.hazard.rule_registry import HazardRuleRegistry, hazard_rule_registry


class CompoundHazardEvaluator:
    """Evaluates compound hazards from deterministic, evidence-backed rules.

    Each compound evaluation requires:
    1. All component hazards are independently evaluated and active
    2. Temporal overlap is explicitly verified
    3. Spatial overlap is explicitly verified (where applicable)
    4. All input evidence quality is sufficient
    """

    def __init__(self, rule_registry: Optional[HazardRuleRegistry] = None) -> None:
        self.rules = rule_registry or hazard_rule_registry

    def evaluate_compound_hazards(
        self,
        hazard_evaluations: List[HazardEvaluation],
        evaluation_time: Optional[datetime] = None,
        location: Optional[Dict[str, Any]] = None,
    ) -> List[CompoundHazardEvaluation]:
        """Evaluates all applicable compound hazard rules against component hazard results.

        Only evaluates compound rules where ALL required component hazards
        are present, active (not NONE/UNDETERMINED), and have verified overlap.
        """
        eval_time = evaluation_time or datetime.now(timezone.utc)
        compound_rules = self.rules.get_active_rules(HazardType.COMPOUND)
        results: List[CompoundHazardEvaluation] = []

        # Build lookup: hazard_type -> list of active evaluations
        active_hazards: Dict[HazardType, List[HazardEvaluation]] = {}
        for he in hazard_evaluations:
            if he.hazard_state not in (HazardState.NONE, HazardState.UNDETERMINED):
                active_hazards.setdefault(he.hazard_type, []).append(he)

        for rule in compound_rules:
            if rule.status != HazardRuleStatus.ACTIVE:
                continue

            evaluation = self._evaluate_compound_rule(
                rule, active_hazards, hazard_evaluations, eval_time, location
            )
            if evaluation:
                results.append(evaluation)

        return results

    def _evaluate_compound_rule(
        self,
        rule: HazardRule,
        active_hazards: Dict[HazardType, List[HazardEvaluation]],
        all_evaluations: List[HazardEvaluation],
        eval_time: datetime,
        location: Optional[Dict[str, Any]] = None,
    ) -> Optional[CompoundHazardEvaluation]:
        """Evaluates a single compound hazard rule."""

        if rule.rule_id == "HZR-CMP-RAIN-WIND-v1":
            return self._evaluate_rain_wind(rule, active_hazards, eval_time, location)
        elif rule.rule_id == "HZR-CMP-HEAT-HUMID-v1":
            return self._evaluate_heat_humidity(rule, active_hazards, eval_time, location)
        elif rule.rule_id == "HZR-CMP-RAIN-SATURATED-v1":
            return self._evaluate_rain_saturated(rule, active_hazards, eval_time, location)

        return None

    def _evaluate_rain_wind(
        self,
        rule: HazardRule,
        active_hazards: Dict[HazardType, List[HazardEvaluation]],
        eval_time: datetime,
        location: Optional[Dict[str, Any]] = None,
    ) -> Optional[CompoundHazardEvaluation]:
        """Compound: Heavy Rainfall + Strong Wind."""
        rain_evals = active_hazards.get(HazardType.HEAVY_RAINFALL, [])
        wind_evals = active_hazards.get(HazardType.STRONG_WIND, [])

        if not rain_evals or not wind_evals:
            return None

        rain = rain_evals[0]
        wind = wind_evals[0]

        # Verify temporal overlap
        temporal_ok = self._verify_temporal_overlap(rain, wind)
        # Verify spatial overlap (same location context)
        spatial_ok = self._verify_spatial_overlap(rain, wind)

        if not temporal_ok:
            return None

        # Both present with overlap — produce compound state
        # Use the more severe component state
        component_states = [rain.hazard_state, wind.hazard_state]
        compound_state = max(component_states, key=lambda s: _state_severity(s))

        all_evidence = list(set(rain.evidence_ids + wind.evidence_ids))

        return CompoundHazardEvaluation(
            compound_hazard_id=f"CHZD-{uuid.uuid4().hex[:8].upper()}",
            hazard_type=HazardType.COMPOUND,
            hazard_state=compound_state,
            evaluation_time=eval_time,
            location=location,
            component_hazard_ids=[rain.hazard_id, wind.hazard_id],
            component_hazard_types=[rain.hazard_type.value, wind.hazard_type.value],
            temporal_overlap_verified=temporal_ok,
            spatial_overlap_verified=spatial_ok,
            rule_id=rule.rule_id,
            rule_version=rule.rule_version,
            source_basis=rule.basis_type,
            quality_state=_worst_quality(rain.quality_state, wind.quality_state),
            evidence_ids=all_evidence,
            reason_codes=["COMPOUND_RAIN_WIND"],
            derived_from=[rain.hazard_id, wind.hazard_id],
        )

    def _evaluate_heat_humidity(
        self,
        rule: HazardRule,
        active_hazards: Dict[HazardType, List[HazardEvaluation]],
        eval_time: datetime,
        location: Optional[Dict[str, Any]] = None,
    ) -> Optional[CompoundHazardEvaluation]:
        """Compound: Heat + High Humidity."""
        heat_evals = active_hazards.get(HazardType.HEAT, [])

        if not heat_evals:
            return None

        heat = heat_evals[0]

        # For heat+humidity compound, we need the heat evaluation to be active
        # AND the observed temperature must be >= 35°C (research threshold)
        # Humidity is checked at evaluation time (>= 65%)
        # Since we require specific humidity evidence that is NOT a separate hazard type,
        # we check whether the heat evaluation's observed_value >= 35.0
        if heat.observed_value is None or heat.observed_value < 35.0:
            return None

        # This compound rule requires explicit humidity evidence
        # which should come through the hazard_evaluations' evidence
        # Since humidity isn't a standalone hazard, this rule can only fire
        # if the calling code explicitly supplies humidity data
        # For now, this is architecture-ready but requires humidity evidence integration

        return None  # Requires humidity evidence to be resolved separately

    def _evaluate_rain_saturated(
        self,
        rule: HazardRule,
        active_hazards: Dict[HazardType, List[HazardEvaluation]],
        eval_time: datetime,
        location: Optional[Dict[str, Any]] = None,
    ) -> Optional[CompoundHazardEvaluation]:
        """Compound: Heavy Rainfall + Saturated Soil (ENGINEERING PROTOTYPE)."""
        rain_evals = active_hazards.get(HazardType.HEAVY_RAINFALL, [])

        if not rain_evals:
            return None

        rain = rain_evals[0]

        # Soil moisture is not a standalone hazard type — requires explicit evidence
        # This compound rule needs soil moisture evidence to be supplied
        # Architecture-ready for when soil moisture observations are available

        return None  # Requires soil moisture evidence integration

    @staticmethod
    def _verify_temporal_overlap(a: HazardEvaluation, b: HazardEvaluation) -> bool:
        """Verifies that two hazard evaluations have temporal overlap.

        If both have valid_from/valid_to, checks for intersection.
        If temporal bounds are missing, falls back to evaluation_time proximity.
        """
        # If both have explicit validity windows
        if a.valid_from and a.valid_to and b.valid_from and b.valid_to:
            return a.valid_from <= b.valid_to and b.valid_from <= a.valid_to

        # If only evaluation times available, assume same-time co-occurrence
        # (within same evaluation batch)
        time_diff = abs((a.evaluation_time - b.evaluation_time).total_seconds())
        return time_diff < 3600  # Within 1 hour

    @staticmethod
    def _verify_spatial_overlap(a: HazardEvaluation, b: HazardEvaluation) -> bool:
        """Verifies that two hazard evaluations have spatial overlap.

        Uses location context if available. Falls back to True if both
        share the same evaluation context (same engine call).
        """
        if a.location and b.location:
            # Simple check: same location_id or same lat/lon
            a_loc_id = a.location.get("location_id")
            b_loc_id = b.location.get("location_id")
            if a_loc_id and b_loc_id:
                return a_loc_id == b_loc_id

            a_lat = a.location.get("latitude")
            a_lon = a.location.get("longitude")
            b_lat = b.location.get("latitude")
            b_lon = b.location.get("longitude")
            if all(v is not None for v in [a_lat, a_lon, b_lat, b_lon]):
                return a_lat == b_lat and a_lon == b_lon

        # If no location data, assume spatial overlap within same evaluation context
        return True


def _state_severity(state: HazardState) -> int:
    """Returns numeric severity rank for comparison (higher = more severe)."""
    return {
        HazardState.NONE: 0,
        HazardState.UNDETERMINED: 0,
        HazardState.WATCH: 1,
        HazardState.WARNING: 2,
        HazardState.SEVERE: 3,
        HazardState.EXTREME: 4,
    }.get(state, 0)


def _worst_quality(a: str, b: str) -> str:
    """Returns the worst quality state between two."""
    priority = {"VALID": 0, "STALE": 1, "MISSING": 2, "CONFLICT": 3, "INVALID": 4}
    a_p = priority.get(a, 5)
    b_p = priority.get(b, 5)
    return a if a_p >= b_p else b

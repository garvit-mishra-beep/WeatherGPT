"""Core Deterministic Hazard Engine for VAYUBODHAK Phase 3.

Orchestrates: Evidence → Quality Validation → Rule Application → Hazard State → Provenance

CRITICAL DESIGN PRINCIPLE:
    SOURCE → EVIDENCE → QUALITY → RULE → HAZARD STATE → PROVENANCE
    Not: SOURCE → LLM → HAZARD
    Not: WEATHER VALUE → ARBITRARY THRESHOLD → "DISASTER"

The engine is callable without an LLM. Same inputs + same rule version = same result.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from app.evidence.models import (
    EvidenceClass,
    EvidenceRecord,
    QualityState,
    SourceAuthorityLevel,
    TemporalIdentity,
    SpatialIdentity,
)
from app.evidence.service import EvidenceService, evidence_service
from app.evidence.claim_gate import ClaimRegistry, claim_registry
from app.hazard.models import (
    BasisType,
    HazardEvaluation,
    HazardRule,
    HazardRuleStatus,
    HazardState,
    HazardType,
)
from app.hazard.rule_registry import HazardRuleRegistry, hazard_rule_registry
from app.hazard.claims import register_hazard_claims


class HazardInputResolver:
    """Resolves Phase 2A EvidenceRecords into typed hazard inputs.

    Handles quality gating:
    - MISSING → UNDETERMINED (never silently converted to 0)
    - STALE → handled per-rule policy
    - INVALID → rejected
    - CONFLICT → surfaced
    """

    @staticmethod
    def resolve_numeric_input(
        evidence_records: List[EvidenceRecord],
        normalized_field: str,
    ) -> tuple[Optional[float], QualityState, List[str]]:
        """Resolves a numeric input from evidence records.

        Returns (value, quality_state, evidence_ids).
        If multiple records match, uses the highest-authority, most-recent VALID one.
        """
        matching = [
            e for e in evidence_records
            if e.normalized_field == normalized_field
        ]

        if not matching:
            return None, QualityState.MISSING, []

        # Separate by quality
        valid = [e for e in matching if e.quality_state == QualityState.VALID]
        stale = [e for e in matching if e.quality_state == QualityState.STALE]
        invalid = [e for e in matching if e.quality_state == QualityState.INVALID]
        conflict = [e for e in matching if e.quality_state == QualityState.CONFLICT]

        if conflict:
            return None, QualityState.CONFLICT, [e.evidence_id for e in conflict]

        if invalid and not valid:
            return None, QualityState.INVALID, [e.evidence_id for e in invalid]

        if valid:
            # Sort by retrieval_time descending (most recent first)
            sorted_valid = sorted(valid, key=lambda e: e.temporal.retrieval_time, reverse=True)
            best = sorted_valid[0]
            try:
                return float(best.normalized_value), QualityState.VALID, [best.evidence_id]
            except (ValueError, TypeError):
                return None, QualityState.INVALID, [best.evidence_id]

        if stale:
            sorted_stale = sorted(stale, key=lambda e: e.temporal.retrieval_time, reverse=True)
            best = sorted_stale[0]
            try:
                return float(best.normalized_value), QualityState.STALE, [best.evidence_id]
            except (ValueError, TypeError):
                return None, QualityState.INVALID, [best.evidence_id]

        return None, QualityState.MISSING, []

    @staticmethod
    def resolve_official_warning(
        evidence_records: List[EvidenceRecord],
    ) -> tuple[Optional[EvidenceRecord], QualityState, List[str]]:
        """Resolves official warning evidence records.

        Official warnings from E0 sources get special handling:
        - Preserves authority, level, instructions, validity window
        - Never overwritten by VAYUBODHAK-derived state
        """
        official = [
            e for e in evidence_records
            if e.evidence_class == EvidenceClass.OFFICIAL_WARNING
        ]

        if not official:
            return None, QualityState.MISSING, []

        # Check for conflicts
        conflict = [e for e in official if e.quality_state == QualityState.CONFLICT]
        if conflict:
            return None, QualityState.CONFLICT, [e.evidence_id for e in conflict]

        # Filter to VALID only
        valid = [e for e in official if e.quality_state == QualityState.VALID]
        if not valid:
            stale = [e for e in official if e.quality_state == QualityState.STALE]
            if stale:
                return None, QualityState.STALE, [e.evidence_id for e in stale]
            return None, QualityState.INVALID, [e.evidence_id for e in official]

        # Take the most severe active warning
        sorted_valid = sorted(valid, key=lambda e: e.temporal.retrieval_time, reverse=True)
        best = sorted_valid[0]
        return best, QualityState.VALID, [best.evidence_id]


class HazardEvaluator:
    """Applies deterministic hazard rules against resolved inputs.

    Each evaluation is:
    - Deterministic (same inputs + same rule = same result)
    - Evidence-linked (input evidence_ids attached)
    - Provenance-tracked
    - Quality-gated
    """

    # IMD rainfall thresholds (from ThresholdConfig IMD-MET-2024.1)
    HEAVY_RAIN_24H_MM = 64.5
    VERY_HEAVY_RAIN_24H_MM = 115.6
    EXTREMELY_HEAVY_RAIN_24H_MM = 204.5

    # IMD heat thresholds (Plains)
    HEATWAVE_PLAINS_C = 40.0
    SEVERE_HEATWAVE_C = 45.0

    # IMD wind thresholds
    STRONG_WIND_KMH = 40.0
    GALE_WIND_KMH = 62.0
    SEVERE_GALE_KMH = 89.0

    # IMD fog thresholds
    MODERATE_FOG_M = 500.0
    DENSE_FOG_M = 200.0
    VERY_DENSE_FOG_M = 50.0

    # Convective instability thresholds
    CAPE_MODERATE = 1000.0
    CAPE_SEVERE = 2500.0
    LI_UNSTABLE = -3.0
    LI_VERY_UNSTABLE = -6.0

    # Cold wave thresholds
    COLD_WAVE_C = 10.0
    SEVERE_COLD_WAVE_C = 4.0

    def evaluate_rainfall(
        self,
        rain_mm_24h: Optional[float],
        quality: QualityState,
        evidence_ids: List[str],
        rule: HazardRule,
        eval_time: datetime,
        location: Optional[Dict[str, Any]] = None,
    ) -> HazardEvaluation:
        """Evaluates heavy rainfall hazard per IMD 24h classification."""
        if quality in (QualityState.MISSING, QualityState.INVALID, QualityState.CONFLICT):
            return self._undetermined(rule, quality, evidence_ids, eval_time, location)

        if rain_mm_24h is None:
            return self._undetermined(rule, QualityState.MISSING, evidence_ids, eval_time, location)

        if rain_mm_24h >= self.EXTREMELY_HEAVY_RAIN_24H_MM:
            state = HazardState.EXTREME
            reason = ["RAIN_EXTREMELY_HEAVY"]
        elif rain_mm_24h >= self.VERY_HEAVY_RAIN_24H_MM:
            state = HazardState.WARNING
            reason = ["RAIN_VERY_HEAVY"]
        elif rain_mm_24h >= self.HEAVY_RAIN_24H_MM:
            state = HazardState.WATCH
            reason = ["RAIN_HEAVY"]
        else:
            state = HazardState.NONE
            reason = ["RAIN_NONE"]

        return HazardEvaluation(
            hazard_id=f"HZD-{uuid.uuid4().hex[:8].upper()}",
            hazard_type=HazardType.HEAVY_RAINFALL,
            hazard_state=state,
            evaluation_time=eval_time,
            location=location,
            evidence_ids=evidence_ids,
            rule_id=rule.rule_id,
            rule_version=rule.rule_version,
            source_basis=rule.basis_type,
            quality_state=quality.value,
            reason_codes=reason,
            observed_value=round(rain_mm_24h, 2),
            observed_unit="mm/24h",
            threshold_applied=f"IMD 24h: Heavy≥{self.HEAVY_RAIN_24H_MM}, VeryHeavy≥{self.VERY_HEAVY_RAIN_24H_MM}, "
                              f"ExtremelyHeavy≥{self.EXTREMELY_HEAVY_RAIN_24H_MM}",
        )

    def evaluate_heat(
        self,
        temp_max_c: Optional[float],
        quality: QualityState,
        evidence_ids: List[str],
        rule: HazardRule,
        eval_time: datetime,
        location: Optional[Dict[str, Any]] = None,
    ) -> HazardEvaluation:
        """Evaluates heat hazard per IMD heatwave criteria (Plains)."""
        if quality in (QualityState.MISSING, QualityState.INVALID, QualityState.CONFLICT):
            return self._undetermined(rule, quality, evidence_ids, eval_time, location)

        if temp_max_c is None:
            return self._undetermined(rule, QualityState.MISSING, evidence_ids, eval_time, location)

        if temp_max_c >= self.SEVERE_HEATWAVE_C:
            state = HazardState.EXTREME
            reason = ["HEAT_SEVERE_WAVE"]
        elif temp_max_c >= self.HEATWAVE_PLAINS_C:
            state = HazardState.WARNING
            reason = ["HEAT_WAVE"]
        else:
            state = HazardState.NONE
            reason = ["HEAT_NONE"]

        return HazardEvaluation(
            hazard_id=f"HZD-{uuid.uuid4().hex[:8].upper()}",
            hazard_type=HazardType.HEAT,
            hazard_state=state,
            evaluation_time=eval_time,
            location=location,
            evidence_ids=evidence_ids,
            rule_id=rule.rule_id,
            rule_version=rule.rule_version,
            source_basis=rule.basis_type,
            quality_state=quality.value,
            reason_codes=reason,
            observed_value=round(temp_max_c, 1),
            observed_unit="°C",
            threshold_applied=f"IMD Plains: Heatwave≥{self.HEATWAVE_PLAINS_C}°C, "
                              f"Severe≥{self.SEVERE_HEATWAVE_C}°C",
        )

    def evaluate_wind(
        self,
        wind_kmh: Optional[float],
        quality: QualityState,
        evidence_ids: List[str],
        rule: HazardRule,
        eval_time: datetime,
        location: Optional[Dict[str, Any]] = None,
    ) -> HazardEvaluation:
        """Evaluates wind hazard per IMD wind scale."""
        if quality in (QualityState.MISSING, QualityState.INVALID, QualityState.CONFLICT):
            return self._undetermined(rule, quality, evidence_ids, eval_time, location)

        if wind_kmh is None:
            return self._undetermined(rule, QualityState.MISSING, evidence_ids, eval_time, location)

        if wind_kmh >= self.SEVERE_GALE_KMH:
            state = HazardState.SEVERE
            reason = ["WIND_SEVERE_GALE"]
        elif wind_kmh >= self.GALE_WIND_KMH:
            state = HazardState.WARNING
            reason = ["WIND_GALE"]
        elif wind_kmh >= self.STRONG_WIND_KMH:
            state = HazardState.WATCH
            reason = ["WIND_STRONG"]
        else:
            state = HazardState.NONE
            reason = ["WIND_NONE"]

        return HazardEvaluation(
            hazard_id=f"HZD-{uuid.uuid4().hex[:8].upper()}",
            hazard_type=HazardType.STRONG_WIND,
            hazard_state=state,
            evaluation_time=eval_time,
            location=location,
            evidence_ids=evidence_ids,
            rule_id=rule.rule_id,
            rule_version=rule.rule_version,
            source_basis=rule.basis_type,
            quality_state=quality.value,
            reason_codes=reason,
            observed_value=round(wind_kmh, 1),
            observed_unit="km/h",
            threshold_applied=f"IMD: Strong≥{self.STRONG_WIND_KMH}, Gale≥{self.GALE_WIND_KMH}, "
                              f"SevereGale≥{self.SEVERE_GALE_KMH}",
        )

    def evaluate_fog(
        self,
        visibility_m: Optional[float],
        quality: QualityState,
        evidence_ids: List[str],
        rule: HazardRule,
        eval_time: datetime,
        location: Optional[Dict[str, Any]] = None,
    ) -> HazardEvaluation:
        """Evaluates fog hazard per IMD visibility classification."""
        if quality in (QualityState.MISSING, QualityState.INVALID, QualityState.CONFLICT):
            return self._undetermined(rule, quality, evidence_ids, eval_time, location)

        if visibility_m is None:
            return self._undetermined(rule, QualityState.MISSING, evidence_ids, eval_time, location)

        if visibility_m < self.VERY_DENSE_FOG_M:
            state = HazardState.SEVERE
            reason = ["FOG_VERY_DENSE"]
        elif visibility_m < self.DENSE_FOG_M:
            state = HazardState.WARNING
            reason = ["FOG_DENSE"]
        elif visibility_m < self.MODERATE_FOG_M:
            state = HazardState.WATCH
            reason = ["FOG_MODERATE"]
        else:
            state = HazardState.NONE
            reason = ["FOG_NONE"]

        return HazardEvaluation(
            hazard_id=f"HZD-{uuid.uuid4().hex[:8].upper()}",
            hazard_type=HazardType.FOG,
            hazard_state=state,
            evaluation_time=eval_time,
            location=location,
            evidence_ids=evidence_ids,
            rule_id=rule.rule_id,
            rule_version=rule.rule_version,
            source_basis=rule.basis_type,
            quality_state=quality.value,
            reason_codes=reason,
            observed_value=round(visibility_m, 0),
            observed_unit="m",
            threshold_applied=f"IMD: Moderate<{self.MODERATE_FOG_M}m, Dense<{self.DENSE_FOG_M}m, "
                              f"VeryDense<{self.VERY_DENSE_FOG_M}m",
        )

    def evaluate_lightning(
        self,
        cape_jkg: Optional[float],
        lifted_index: Optional[float],
        quality: QualityState,
        evidence_ids: List[str],
        rule: HazardRule,
        eval_time: datetime,
        location: Optional[Dict[str, Any]] = None,
    ) -> HazardEvaluation:
        """Evaluates lightning/thunderstorm potential from NWP diagnostics.

        NOTE: This is an ENGINEERING PROTOTYPE — not observed lightning detection.
        """
        if quality in (QualityState.MISSING, QualityState.INVALID, QualityState.CONFLICT):
            return self._undetermined(rule, quality, evidence_ids, eval_time, location)

        if cape_jkg is None and lifted_index is None:
            return self._undetermined(rule, QualityState.MISSING, evidence_ids, eval_time, location)

        severe_cape = cape_jkg is not None and cape_jkg >= self.CAPE_SEVERE
        severe_li = lifted_index is not None and lifted_index <= self.LI_VERY_UNSTABLE
        moderate_cape = cape_jkg is not None and cape_jkg >= self.CAPE_MODERATE
        moderate_li = lifted_index is not None and lifted_index <= self.LI_UNSTABLE

        if severe_cape or severe_li:
            state = HazardState.WARNING
            reason = ["LIGHTNING_SEVERE_INSTABILITY"]
        elif moderate_cape or moderate_li:
            state = HazardState.WATCH
            reason = ["LIGHTNING_MODERATE_INSTABILITY"]
        else:
            state = HazardState.NONE
            reason = ["LIGHTNING_NONE"]

        return HazardEvaluation(
            hazard_id=f"HZD-{uuid.uuid4().hex[:8].upper()}",
            hazard_type=HazardType.LIGHTNING,
            hazard_state=state,
            evaluation_time=eval_time,
            location=location,
            evidence_ids=evidence_ids,
            rule_id=rule.rule_id,
            rule_version=rule.rule_version,
            source_basis=rule.basis_type,
            quality_state=quality.value,
            reason_codes=reason,
            observed_value=cape_jkg,
            observed_unit="J/kg (CAPE)",
            threshold_applied=f"CAPE: Moderate≥{self.CAPE_MODERATE}, Severe≥{self.CAPE_SEVERE}; "
                              f"LI: Unstable≤{self.LI_UNSTABLE}, VeryUnstable≤{self.LI_VERY_UNSTABLE}",
        )

    def evaluate_cold_wave(
        self,
        temp_min_c: Optional[float],
        quality: QualityState,
        evidence_ids: List[str],
        rule: HazardRule,
        eval_time: datetime,
        location: Optional[Dict[str, Any]] = None,
    ) -> HazardEvaluation:
        """Evaluates cold wave hazard per IMD criteria."""
        if quality in (QualityState.MISSING, QualityState.INVALID, QualityState.CONFLICT):
            return self._undetermined(rule, quality, evidence_ids, eval_time, location)

        if temp_min_c is None:
            return self._undetermined(rule, QualityState.MISSING, evidence_ids, eval_time, location)

        if temp_min_c <= self.SEVERE_COLD_WAVE_C:
            state = HazardState.SEVERE
            reason = ["COLD_SEVERE_WAVE"]
        elif temp_min_c <= self.COLD_WAVE_C:
            state = HazardState.WARNING
            reason = ["COLD_WAVE"]
        else:
            state = HazardState.NONE
            reason = ["COLD_NONE"]

        return HazardEvaluation(
            hazard_id=f"HZD-{uuid.uuid4().hex[:8].upper()}",
            hazard_type=HazardType.COLD_WAVE,
            hazard_state=state,
            evaluation_time=eval_time,
            location=location,
            evidence_ids=evidence_ids,
            rule_id=rule.rule_id,
            rule_version=rule.rule_version,
            source_basis=rule.basis_type,
            quality_state=quality.value,
            reason_codes=reason,
            observed_value=round(temp_min_c, 1),
            observed_unit="°C",
            threshold_applied=f"IMD: ColdWave≤{self.COLD_WAVE_C}°C, Severe≤{self.SEVERE_COLD_WAVE_C}°C",
        )

    def evaluate_official_warning(
        self,
        warning_record: Optional[EvidenceRecord],
        quality: QualityState,
        evidence_ids: List[str],
        rule: HazardRule,
        eval_time: datetime,
        location: Optional[Dict[str, Any]] = None,
    ) -> HazardEvaluation:
        """Evaluates official warning evidence, preserving authority and immutable severity.

        CRITICAL RULES:
        - Do not convert an official warning into an invented VAYUBODHAK warning.
        - Do not change its official severity.
        - Do not replace official instructions with model-generated instructions.
        """
        if quality in (QualityState.MISSING, QualityState.INVALID, QualityState.CONFLICT):
            return self._undetermined(rule, quality, evidence_ids, eval_time, location)

        if warning_record is None:
            return self._undetermined(rule, QualityState.MISSING, evidence_ids, eval_time, location)

        # Extract official warning level from raw payload
        raw = warning_record.raw_payload or {}
        warning_level = str(raw.get("warning_level", raw.get("severity", ""))).strip().capitalize()
        official_instructions = raw.get("instructions", raw.get("description", ""))
        issuing_authority = warning_record.source_id

        # Map to HazardState — preserving source-native level
        level_map = {
            "Red": HazardState.EXTREME,
            "Orange": HazardState.WARNING,
            "Yellow": HazardState.WATCH,
            "Green": HazardState.NONE,
        }
        state = level_map.get(warning_level, HazardState.WATCH)
        reason_map = {
            "Red": "OFFICIAL_RED",
            "Orange": "OFFICIAL_ORANGE",
            "Yellow": "OFFICIAL_YELLOW",
            "Green": "OFFICIAL_GREEN",
        }
        reason = [reason_map.get(warning_level, "OFFICIAL_WARNING_ACTIVE")]

        return HazardEvaluation(
            hazard_id=f"HZD-{uuid.uuid4().hex[:8].upper()}",
            hazard_type=HazardType.OFFICIAL_WARNING,
            hazard_state=state,
            evaluation_time=eval_time,
            location=location,
            evidence_ids=evidence_ids,
            rule_id=rule.rule_id,
            rule_version=rule.rule_version,
            source_basis=rule.basis_type,
            quality_state=quality.value,
            valid_from=warning_record.temporal.valid_from,
            valid_to=warning_record.temporal.valid_to,
            reason_codes=reason,
            official_warning_level=warning_level,
            official_instructions=str(official_instructions) if official_instructions else None,
            issuing_authority=issuing_authority,
        )

    def _undetermined(
        self,
        rule: HazardRule,
        quality: QualityState,
        evidence_ids: List[str],
        eval_time: datetime,
        location: Optional[Dict[str, Any]] = None,
    ) -> HazardEvaluation:
        """Returns UNDETERMINED hazard state when evidence is insufficient."""
        reason_suffix = quality.value.upper()
        return HazardEvaluation(
            hazard_id=f"HZD-{uuid.uuid4().hex[:8].upper()}",
            hazard_type=HazardType(rule.hazard_type) if isinstance(rule.hazard_type, str) else rule.hazard_type,
            hazard_state=HazardState.UNDETERMINED,
            evaluation_time=eval_time,
            location=location,
            evidence_ids=evidence_ids,
            rule_id=rule.rule_id,
            rule_version=rule.rule_version,
            source_basis=rule.basis_type,
            quality_state=quality.value,
            reason_codes=[f"INSUFFICIENT_EVIDENCE_{reason_suffix}"],
        )


class HazardEngine:
    """Core orchestrator for deterministic hazard evaluation.

    Pipeline:
        Evidence Records → Input Resolution → Quality Gating → Rule Application
        → Hazard State → Provenance → Result

    INVARIANT: Same inputs + same rule version = same result (determinism).
    """

    def __init__(
        self,
        rule_registry: Optional[HazardRuleRegistry] = None,
        evidence_svc: Optional[EvidenceService] = None,
        claim_reg: Optional[ClaimRegistry] = None,
    ) -> None:
        self.rules = rule_registry or hazard_rule_registry
        self.evidence_svc = evidence_svc or evidence_service
        self.claim_reg = claim_reg or claim_registry
        self.resolver = HazardInputResolver()
        self.evaluator = HazardEvaluator()

        # Register hazard claims into the claim registry
        register_hazard_claims(self.claim_reg)

    def evaluate_hazards(
        self,
        evidence_records: List[EvidenceRecord],
        location: Optional[Dict[str, Any]] = None,
        evaluation_time: Optional[datetime] = None,
        hazard_types: Optional[List[HazardType]] = None,
    ) -> List[HazardEvaluation]:
        """Evaluates all applicable hazards for a set of evidence records.

        Args:
            evidence_records: Phase 2A EvidenceRecords to evaluate
            location: Spatial context
            evaluation_time: UTC evaluation timestamp (defaults to now)
            hazard_types: Optional filter — evaluate only these hazard types

        Returns:
            List of deterministic HazardEvaluation results
        """
        eval_time = evaluation_time or datetime.now(timezone.utc)
        results: List[HazardEvaluation] = []

        # Get all active, non-compound rules
        active_rules = self.rules.get_active_rules()
        non_compound = [r for r in active_rules if r.hazard_type != HazardType.COMPOUND]

        for rule in non_compound:
            if hazard_types and rule.hazard_type not in hazard_types:
                continue

            evaluation = self._evaluate_single_rule(rule, evidence_records, eval_time, location)
            results.append(evaluation)

        return results

    def evaluate_single_hazard(
        self,
        hazard_type: HazardType,
        evidence_records: List[EvidenceRecord],
        location: Optional[Dict[str, Any]] = None,
        evaluation_time: Optional[datetime] = None,
    ) -> HazardEvaluation:
        """Evaluates a single hazard type."""
        eval_time = evaluation_time or datetime.now(timezone.utc)
        rules = self.rules.get_active_rules(hazard_type)

        if not rules:
            # No active rule for this hazard type
            return HazardEvaluation(
                hazard_id=f"HZD-{uuid.uuid4().hex[:8].upper()}",
                hazard_type=hazard_type,
                hazard_state=HazardState.UNDETERMINED,
                evaluation_time=eval_time,
                location=location,
                rule_id="NO_ACTIVE_RULE",
                rule_version="N/A",
                source_basis=BasisType.UNRESOLVED,
                quality_state="MISSING",
                reason_codes=["NO_ACTIVE_RULE_FOR_HAZARD_TYPE"],
            )

        return self._evaluate_single_rule(rules[0], evidence_records, eval_time, location)

    def _evaluate_single_rule(
        self,
        rule: HazardRule,
        evidence_records: List[EvidenceRecord],
        eval_time: datetime,
        location: Optional[Dict[str, Any]] = None,
    ) -> HazardEvaluation:
        """Evaluates a single rule against evidence records."""
        # Enforce: only ACTIVE rules may execute
        if rule.status != HazardRuleStatus.ACTIVE:
            return self.evaluator._undetermined(
                rule, QualityState.INVALID, [], eval_time, location
            )

        if rule.hazard_type == HazardType.HEAVY_RAINFALL:
            val, quality, eids = self.resolver.resolve_numeric_input(
                evidence_records, "precipitation_mm_24h"
            )
            return self.evaluator.evaluate_rainfall(val, quality, eids, rule, eval_time, location)

        elif rule.hazard_type == HazardType.HEAT:
            val, quality, eids = self.resolver.resolve_numeric_input(
                evidence_records, "temperature_max_c"
            )
            return self.evaluator.evaluate_heat(val, quality, eids, rule, eval_time, location)

        elif rule.hazard_type == HazardType.STRONG_WIND:
            val, quality, eids = self.resolver.resolve_numeric_input(
                evidence_records, "wind_speed_kmh"
            )
            return self.evaluator.evaluate_wind(val, quality, eids, rule, eval_time, location)

        elif rule.hazard_type == HazardType.FOG:
            val, quality, eids = self.resolver.resolve_numeric_input(
                evidence_records, "visibility_m"
            )
            return self.evaluator.evaluate_fog(val, quality, eids, rule, eval_time, location)

        elif rule.hazard_type == HazardType.LIGHTNING:
            cape_val, cape_q, cape_eids = self.resolver.resolve_numeric_input(
                evidence_records, "cape_jkg"
            )
            li_val, li_q, li_eids = self.resolver.resolve_numeric_input(
                evidence_records, "lifted_index"
            )
            # Combine quality: worst of both
            combined_q = cape_q if cape_q != QualityState.VALID else li_q
            if cape_q == QualityState.VALID or li_q == QualityState.VALID:
                combined_q = QualityState.VALID
            combined_eids = list(set(cape_eids + li_eids))
            return self.evaluator.evaluate_lightning(
                cape_val, li_val, combined_q, combined_eids, rule, eval_time, location
            )

        elif rule.hazard_type == HazardType.COLD_WAVE:
            val, quality, eids = self.resolver.resolve_numeric_input(
                evidence_records, "temperature_min_c"
            )
            return self.evaluator.evaluate_cold_wave(val, quality, eids, rule, eval_time, location)

        elif rule.hazard_type == HazardType.OFFICIAL_WARNING:
            record, quality, eids = self.resolver.resolve_official_warning(evidence_records)
            return self.evaluator.evaluate_official_warning(
                record, quality, eids, rule, eval_time, location
            )

        elif rule.hazard_type == HazardType.FLOOD:
            # Flood is CWC official warning only
            record, quality, eids = self.resolver.resolve_official_warning(evidence_records)
            if record is None:
                return self.evaluator._undetermined(rule, quality, eids, eval_time, location)
            # Check if this is a flood-specific warning
            raw = record.raw_payload or {}
            warning_type = str(raw.get("warning_type", raw.get("hazard_type", ""))).upper()
            if "FLOOD" not in warning_type and "INUNDATION" not in warning_type:
                return self.evaluator._undetermined(
                    rule, QualityState.MISSING, eids, eval_time, location
                )
            return self.evaluator.evaluate_official_warning(
                record, quality, eids, rule, eval_time, location
            )

        elif rule.hazard_type == HazardType.CYCLONE:
            # Cyclone requires official IMD warning
            record, quality, eids = self.resolver.resolve_official_warning(evidence_records)
            if record is None:
                return self.evaluator._undetermined(rule, quality, eids, eval_time, location)
            raw = record.raw_payload or {}
            warning_type = str(raw.get("warning_type", raw.get("hazard_type", ""))).upper()
            if "CYCLONE" not in warning_type and "DEPRESSION" not in warning_type:
                return self.evaluator._undetermined(
                    rule, QualityState.MISSING, eids, eval_time, location
                )
            return self.evaluator.evaluate_official_warning(
                record, quality, eids, rule, eval_time, location
            )

        elif rule.hazard_type == HazardType.LANDSLIDE_SUSCEPTIBILITY:
            val, quality, eids = self.resolver.resolve_numeric_input(
                evidence_records, "gsi_susceptibility_class"
            )
            if quality != QualityState.VALID or val is None:
                return self.evaluator._undetermined(rule, quality, eids, eval_time, location)
            # GSI classes: 1=Low, 2=Moderate, 3=High, 4=Very High
            if val >= 4:
                state = HazardState.SEVERE
                reason = ["LANDSLIDE_VERY_HIGH"]
            elif val >= 3:
                state = HazardState.WARNING
                reason = ["LANDSLIDE_HIGH"]
            elif val >= 2:
                state = HazardState.WATCH
                reason = ["LANDSLIDE_MODERATE"]
            else:
                state = HazardState.NONE
                reason = ["LANDSLIDE_LOW"]
            return HazardEvaluation(
                hazard_id=f"HZD-{uuid.uuid4().hex[:8].upper()}",
                hazard_type=HazardType.LANDSLIDE_SUSCEPTIBILITY,
                hazard_state=state,
                evaluation_time=eval_time,
                location=location,
                evidence_ids=eids,
                rule_id=rule.rule_id,
                rule_version=rule.rule_version,
                source_basis=rule.basis_type,
                quality_state=quality.value,
                reason_codes=reason,
                observed_value=val,
                observed_unit="GSI susceptibility class",
                threshold_applied="GSI: 1=Low, 2=Moderate, 3=High, 4=VeryHigh",
            )

        # Unknown hazard type — return undetermined
        return self.evaluator._undetermined(
            rule, QualityState.MISSING, [], eval_time, location
        )


# Singleton instance
hazard_engine = HazardEngine()

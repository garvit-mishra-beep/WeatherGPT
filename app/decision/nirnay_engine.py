"""Canonical Nirnay Engine for VAYUBODHAK Phase 8 — Decision Support & Nirnay Engine.

Implements the end-to-end deterministic decision support layer:
Evidence → Validated Hazard → Exposure → Vulnerability → Risk → Potential Impact → Decision Engine → NirnayCard → Human Action

Core Invariants:
1. Zero LLM dependency in the critical numerical and action path.
2. Official warnings pass through verbatim with preserved authority.
3. System recommendations are strictly distinguished from statutory government orders.
4. Consequential actions require explicit human verification.
5. Missing or unknown evidence NEVER converts to 'safe' or 'no threat'.
6. Full cryptographic provenance and change detection against historical decisions.
7. Future-dated warnings (valid_from > now) are marked SCHEDULED and never activate early.
8. Expired warnings (valid_to < now) are marked EXPIRED and never activate emergency directives.
9. Official text, system summary, and localized translation are strictly segregated.
10. Prototype upstream impacts (e.g. road waterlogging) strictly remain prototype advisories.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from app.decision.claims import decision_claim_validator
from app.decision.models import (
    ActionCategory,
    ActionRecommendation,
    ActionSource,
    ChangeReasonCode,
    ConfidenceLevel,
    DecisionChangeRecord,
    DecisionContext,
    DecisionOutcome,
    DecisionPackage,
    DecisionRule,
    DecisionState,
    NirnayCard,
    OfficialWarningInfo,
    PriorityClass,
    SeverityLevel,
)
from app.decision.rule_registry import decision_rule_registry
from app.hazard.models import HazardEvaluation, HazardState, HazardType
from app.impact.models import DamageState, ImpactEvaluationBundle, PotentialImpactAssessment
from app.risk.models import RiskAssessment, RiskCategory

logger = logging.getLogger(__name__)


class NirnayEngine:
    """Deterministic Decision Support and Nirnay Card generation engine."""

    def __init__(self) -> None:
        self.registry = decision_rule_registry
        self.claim_validator = decision_claim_validator

    def evaluate(
        self,
        hazard: Optional[HazardEvaluation] = None,
        exposure_summary: Optional[Dict[str, Any]] = None,
        risk: Optional[RiskAssessment] = None,
        impact_bundle: Optional[ImpactEvaluationBundle] = None,
        official_warnings: Optional[List[OfficialWarningInfo]] = None,
        evidence_quality: str = "VALID",
        data_coverage: float = 1.0,
        staleness_state: str = "FRESH",
        geography: str = "Target District",
        spatial_resolution: str = "district",
        previous_decision: Optional[DecisionPackage] = None,
        now_dt: Optional[datetime] = None,
    ) -> DecisionPackage:
        """Deterministically evaluates decision state, eligible rules, and emits a DecisionPackage."""
        now_dt = now_dt or datetime.now(timezone.utc)
        decision_id = f"DEC-{uuid.uuid4().hex[:8].upper()}"
        assessment_time_iso = now_dt.isoformat()

        # Track version sequence across lineage
        version = 1
        if previous_decision is not None:
            prev_ver = getattr(previous_decision.decision, "version", 1)
            version = prev_ver + 1

        # --------------------------------------------------------------------
        # 1. Quality Gate & Quality State Assessment
        # --------------------------------------------------------------------
        q_upper = evidence_quality.upper()
        if q_upper == "INVALID":
            raise ValueError("Decision blocked: upstream evidence is INVALID")

        is_conflict = (q_upper == "CONFLICT")
        is_insufficient = (q_upper in ["MISSING", "INSUFFICIENT_EVIDENCE"] or data_coverage < 0.5)
        is_stale_hazard = (staleness_state.upper() in ["STALE", "EXPIRED"])

        # --------------------------------------------------------------------
        # 2. Process Official Warnings (Future-Dated, Active & Expired)
        # --------------------------------------------------------------------
        active_warnings, scheduled_warnings, expired_warnings = self._filter_warnings(
            official_warnings or [], now_dt
        )
        primary_warning: Optional[OfficialWarningInfo] = active_warnings[0] if active_warnings else None
        has_official_warning = (primary_warning is not None)
        has_official_evacuation = any(w.evacuation_ordered for w in active_warnings)
        has_official_closure = any(w.road_closure_ordered for w in active_warnings)

        # --------------------------------------------------------------------
        # 3. Upstream State & Precondition Extraction
        # --------------------------------------------------------------------
        hazard_type = "WEATHER"
        hazard_state = "NONE"
        hazard_id = None
        if hazard is not None:
            hazard_id = getattr(hazard, "hazard_id", getattr(hazard, "evaluation_id", None))
            hazard_type = getattr(hazard.hazard_type, "value", str(hazard.hazard_type)).upper()
            raw_state = getattr(hazard, "hazard_state", getattr(hazard, "severity_tier", "NONE"))
            hazard_state = getattr(raw_state, "value", str(raw_state)).upper()

        risk_tier_str = None
        risk_id = None
        if risk is not None:
            risk_id = getattr(risk, "assessment_id", getattr(risk, "risk_id", None))
            raw_risk = getattr(risk, "risk_category", getattr(risk, "risk_tier", None))
            if raw_risk is not None:
                risk_tier_str = getattr(raw_risk, "value", str(raw_risk)).upper()

        impact_id = None
        impact_conds: Dict[str, Any] = {}
        impact_summary: Dict[str, Any] = {}
        if impact_bundle is not None:
            impact_id = impact_bundle.bundle_id
            impact_summary = self._summarize_impacts(impact_bundle)
            impact_conds = self._extract_impact_conditions(impact_bundle)

        # --------------------------------------------------------------------
        # 4. Determine Governing Decision State
        # --------------------------------------------------------------------
        decision_state = self._determine_decision_state(
            is_conflict=is_conflict,
            is_insufficient=is_insufficient,
            is_stale_hazard=is_stale_hazard,
            has_official_evacuation=has_official_evacuation,
            has_official_warning=has_official_warning,
            hazard_state=hazard_state,
            risk_tier=risk_tier_str,
            impact_conds=impact_conds,
        )

        # --------------------------------------------------------------------
        # 5. Evaluate Eligible Decision Rules (Including Governed Risk Mappings)
        # --------------------------------------------------------------------
        eligible_rules = self.registry.find_eligible_rules(
            hazard_type=hazard_type,
            hazard_state=hazard_state,
            quality_state=evidence_quality,
            has_official_source=has_official_warning,
            has_official_evacuation=has_official_evacuation,
            impact_conditions=impact_conds,
            risk_tier=risk_tier_str,
        )

        # --------------------------------------------------------------------
        # 6. Generate Action Recommendations
        # --------------------------------------------------------------------
        recommendations = self._generate_recommendations(
            eligible_rules=eligible_rules,
            primary_warning=primary_warning,
            has_official_evacuation=has_official_evacuation,
            has_official_closure=has_official_closure,
            evidence_quality=evidence_quality,
            geography=geography,
            impact_conds=impact_conds,
            risk_tier=risk_tier_str,
            active_warnings=active_warnings,
        )

        human_verification_required = any(a.human_verification_required for a in recommendations)
        decision_conditions = self._build_decision_conditions(
            hazard_type=hazard_type,
            hazard_state=hazard_state,
            evidence_quality=evidence_quality,
            has_official_warning=has_official_warning,
            impact_conds=impact_conds,
            decision_state=decision_state,
            risk_tier=risk_tier_str,
        )

        # --------------------------------------------------------------------
        # 7. Cryptographic Provenance & Audit
        # --------------------------------------------------------------------
        method_ids = [r.rule_id for r in eligible_rules]
        claim_ids = [r.claim_id for r in eligible_rules if r.claim_id]
        action_categories = [a.category.value for a in recommendations]
        provenance_id = self._calculate_provenance_hash(
            decision_id=decision_id,
            version=version,
            hazard_id=hazard_id,
            exposure_id=exposure_summary.get("exposure_id") if exposure_summary else None,
            vulnerability_id=None,
            risk_id=risk_id,
            impact_id=impact_id,
            method_ids=method_ids,
            rule_version="1.0.0",
            decision_state=decision_state.value,
            action_categories=action_categories,
            official_warning_ids=[w.alert_id for w in active_warnings],
            claim_ids=claim_ids,
        )

        # Prohibited actions audit
        prohibited_actions = [
            "Autonomous statutory evacuation order",
            "Autonomous statutory road closure",
            "Casualty or fatality prediction",
            "Guaranteed financial or yield loss assertion",
        ]
        if is_insufficient:
            prohibited_actions.append("Assertion of safety or zero-risk condition")

        # --------------------------------------------------------------------
        # 8. Decision Context Model
        # --------------------------------------------------------------------
        decision_context = DecisionContext(
            decision_id=decision_id,
            version=version,
            assessment_time_iso=assessment_time_iso,
            hazard_evaluation_id=hazard_id,
            exposure_id=exposure_summary.get("exposure_id") if exposure_summary else None,
            vulnerability_id=None,
            risk_id=risk_id,
            impact_id=impact_id,
            hazard_type=hazard_type,
            hazard_state=hazard_state,
            geography=geography,
            spatial_resolution=spatial_resolution,
            official_warning_present=has_official_warning,
            official_warning_ids=[w.alert_id for w in active_warnings],
            risk_level=risk_tier_str,
            impact_summary=impact_summary,
            evidence_quality=evidence_quality,
            data_coverage=data_coverage,
            staleness_state=staleness_state,
            decision_conditions=decision_conditions,
            eligible_actions=recommendations,
            prohibited_actions=prohibited_actions,
            method_ids=method_ids,
            claim_ids=claim_ids,
            provenance_id=provenance_id,
            uncertainty={
                "data_coverage": data_coverage,
                "staleness_state": staleness_state,
                "quality_state": evidence_quality,
                "impact_model_type": "VAYUBODHAK_PROTOTYPE",
                "loss_calibration_status": "UNBOUNDED_SCENARIO_APPROXIMATION",
            },
            human_verification_required=human_verification_required,
            decision_status=decision_state,
        )

        # --------------------------------------------------------------------
        # 9. Change Detection Against Previous Decision
        # --------------------------------------------------------------------
        change_record = None
        if previous_decision is not None:
            change_record = self._detect_decision_change(
                current_id=decision_id,
                current_state=decision_state,
                previous_decision=previous_decision,
                now_iso=assessment_time_iso,
            )

        # --------------------------------------------------------------------
        # 10. Construct Canonical NirnayCard
        # --------------------------------------------------------------------
        nirnay_card = self._build_nirnay_card(
            decision_context=decision_context,
            primary_warning=primary_warning,
            recommendations=recommendations,
            geography=geography,
            now_iso=assessment_time_iso,
            scheduled_warnings=scheduled_warnings,
        )

        # --------------------------------------------------------------------
        # 11. Emit Canonical DecisionPackage
        # --------------------------------------------------------------------
        return DecisionPackage(
            decision_id=decision_id,
            timestamp_iso=assessment_time_iso,
            decision=decision_context,
            nirnay_card=nirnay_card,
            official_information=primary_warning,
            recommendations=recommendations,
            verification={
                "human_verification_required": human_verification_required,
                "verification_status": "PENDING" if human_verification_required else "NOT_REQUIRED",
                "verified_by": None,
                "verification_note": None,
            },
            provenance={
                "provenance_hash": provenance_id,
                "version": version,
                "hazard_id": hazard_id,
                "risk_id": risk_id,
                "impact_id": impact_id,
                "rules_evaluated": method_ids,
                "claims_referenced": claim_ids,
                "change_record": change_record.model_dump() if change_record else None,
            },
            uncertainty=decision_context.uncertainty,
            limitations=[
                "Decision recommendations do not replace statutory local disaster management authorities",
                "Potential impact estimates are prototype heuristics and not calibrated real-world loss predictions",
                "Zero automated statutory commands or casualty predictions are generated",
            ],
        )

    # ========================================================================
    # Internal Evaluation Helpers
    # ========================================================================

    def _filter_warnings(
        self,
        warnings: List[OfficialWarningInfo],
        now_dt: datetime,
    ) -> Tuple[List[OfficialWarningInfo], List[OfficialWarningInfo], List[OfficialWarningInfo]]:
        """Filters active, scheduled (future-dated), and expired official warnings preserving exact validity.
        
        Guarantees:
        - Warnings with valid_from > now_dt are marked SCHEDULED and are NOT active.
        - Warnings with valid_to < now_dt are marked EXPIRED and are NOT active.
        - Only warnings currently within validity bounds (valid_from <= now_dt <= valid_to) are ACTIVE.
        - Verbatim text is preserved in official_text.
        """
        active: List[OfficialWarningInfo] = []
        scheduled: List[OfficialWarningInfo] = []
        expired: List[OfficialWarningInfo] = []

        for w in warnings:
            # Preserve verbatim official text
            official_txt = w.official_text or w.instruction or w.description or w.headline or ""

            is_future = False
            if w.valid_from_iso:
                try:
                    v_from = datetime.fromisoformat(w.valid_from_iso.replace("Z", "+00:00"))
                    if v_from > now_dt:
                        is_future = True
                except Exception:
                    pass

            is_exp = False
            if w.valid_to_iso:
                try:
                    v_to = datetime.fromisoformat(w.valid_to_iso.replace("Z", "+00:00"))
                    if v_to < now_dt:
                        is_exp = True
                except Exception:
                    pass

            if is_exp or w.is_expired or w.status == "EXPIRED":
                exp_obj = OfficialWarningInfo(
                    alert_id=w.alert_id,
                    source=w.source,
                    authority=w.authority,
                    warning_level=w.warning_level,
                    hazard_type=w.hazard_type,
                    headline=w.headline,
                    description=w.description,
                    instruction=w.instruction,
                    issue_time_iso=w.issue_time_iso,
                    valid_from_iso=w.valid_from_iso,
                    valid_to_iso=w.valid_to_iso,
                    geography=w.geography,
                    retrieval_time_iso=w.retrieval_time_iso,
                    is_expired=True,
                    status="EXPIRED",
                    official_text=official_txt,
                    system_summary=w.system_summary,
                    translated_text=w.translated_text,
                    source_locator=w.source_locator,
                    authoritative_field="official_text",
                    is_official=w.is_official,
                    evacuation_ordered=w.evacuation_ordered,
                    road_closure_ordered=w.road_closure_ordered,
                )
                expired.append(exp_obj)
            elif is_future or w.status == "SCHEDULED":
                sched_obj = OfficialWarningInfo(
                    alert_id=w.alert_id,
                    source=w.source,
                    authority=w.authority,
                    warning_level=w.warning_level,
                    hazard_type=w.hazard_type,
                    headline=w.headline,
                    description=w.description,
                    instruction=w.instruction,
                    issue_time_iso=w.issue_time_iso,
                    valid_from_iso=w.valid_from_iso,
                    valid_to_iso=w.valid_to_iso,
                    geography=w.geography,
                    retrieval_time_iso=w.retrieval_time_iso,
                    is_expired=False,
                    status="SCHEDULED",
                    official_text=official_txt,
                    system_summary=w.system_summary,
                    translated_text=w.translated_text,
                    source_locator=w.source_locator,
                    authoritative_field="official_text",
                    is_official=w.is_official,
                    evacuation_ordered=w.evacuation_ordered,
                    road_closure_ordered=w.road_closure_ordered,
                )
                scheduled.append(sched_obj)
            else:
                active_obj = OfficialWarningInfo(
                    alert_id=w.alert_id,
                    source=w.source,
                    authority=w.authority,
                    warning_level=w.warning_level,
                    hazard_type=w.hazard_type,
                    headline=w.headline,
                    description=w.description,
                    instruction=w.instruction,
                    issue_time_iso=w.issue_time_iso,
                    valid_from_iso=w.valid_from_iso,
                    valid_to_iso=w.valid_to_iso,
                    geography=w.geography,
                    retrieval_time_iso=w.retrieval_time_iso,
                    is_expired=False,
                    status="ACTIVE",
                    official_text=official_txt,
                    system_summary=w.system_summary or f"Active {w.warning_level} warning issued by {w.authority} for {w.geography}",
                    translated_text=w.translated_text,
                    source_locator=w.source_locator,
                    authoritative_field="official_text",
                    is_official=w.is_official,
                    evacuation_ordered=w.evacuation_ordered,
                    road_closure_ordered=w.road_closure_ordered,
                )
                active.append(active_obj)

        return active, scheduled, expired

    def _determine_decision_state(
        self,
        is_conflict: bool,
        is_insufficient: bool,
        is_stale_hazard: bool,
        has_official_evacuation: bool,
        has_official_warning: bool,
        hazard_state: str,
        risk_tier: Optional[str],
        impact_conds: Dict[str, Any],
    ) -> DecisionState:
        """Determines governing state machine state."""
        if is_conflict:
            return DecisionState.REVIEW_REQUIRED

        if is_insufficient:
            return DecisionState.INSUFFICIENT_EVIDENCE

        if is_stale_hazard and hazard_state in ["WARNING", "SEVERE", "EXTREME"]:
            # Stale rapid hazard blocks emergency action; review required
            return DecisionState.REVIEW_REQUIRED

        if has_official_evacuation:
            return DecisionState.OFFICIAL_ACTION_AVAILABLE

        if has_official_warning:
            return DecisionState.OFFICIAL_ACTION_AVAILABLE

        if hazard_state in ["SEVERE", "EXTREME"] or risk_tier in ["HIGH", "VERY_HIGH"]:
            return DecisionState.PREPARE

        if impact_conds.get("road_disrupted") or impact_conds.get("hospital_strain"):
            return DecisionState.ACTION_RECOMMENDED

        if hazard_state in ["WATCH", "WARNING"] or risk_tier in ["MODERATE"]:
            return DecisionState.MONITOR

        return DecisionState.NO_SIGNAL

    def _summarize_impacts(self, bundle: Any) -> Dict[str, Any]:
        """Summarizes sectoral impacts for decision context."""
        summary: Dict[str, Any] = {}
        assessments = getattr(bundle, "assessments", []) or []

        buildings = getattr(bundle, "building_impacts", None) or [a for a in assessments if getattr(a, "entity_type", "").upper() == "BUILDING"]
        roads = getattr(bundle, "road_impacts", None) or [a for a in assessments if getattr(a, "entity_type", "").upper() == "ROAD"]
        hospitals = getattr(bundle, "hospital_impacts", None) or [a for a in assessments if getattr(a, "entity_type", "").upper() == "HOSPITAL"]
        schools = getattr(bundle, "school_impacts", None) or [a for a in assessments if getattr(a, "entity_type", "").upper() == "SCHOOL"]
        agri = getattr(bundle, "agricultural_impacts", None) or [a for a in assessments if getattr(a, "entity_type", "").upper() == "AGRICULTURE"]

        if buildings:
            summary["buildings_evaluated"] = len(buildings)
            summary["severe_building_damage"] = any(
                getattr(b, "damage_state", None) in [DamageState.MAJOR, DamageState.SEVERE] for b in buildings
            )
        if roads:
            summary["roads_evaluated"] = len(roads)
            summary["max_disrupted_length_km"] = max(
                (getattr(r, "disrupted_quantity", None) or getattr(r, "disrupted_length_km", 0.0) or 0.0 for r in roads),
                default=0.0,
            )
        if hospitals:
            summary["hospitals_evaluated"] = len(hospitals)
            summary["beds_at_risk"] = sum(
                (getattr(h, "disrupted_quantity", None) or getattr(h, "inpatient_beds_at_risk", 0.0) or getattr(h, "details", {}).get("inpatient_beds_at_risk", 0.0) or 0.0)
                for h in hospitals
            )
        if schools:
            summary["schools_evaluated"] = len(schools)
            summary["shelter_candidates"] = sum(
                1 for s in schools if getattr(s, "shelter_suitability_flag", False) or getattr(s, "details", {}).get("shelter_suitability_flag", False)
            )
        if agri:
            summary["agricultural_crops_evaluated"] = len(agri)
            summary["production_loss_tonnes"] = sum(
                (getattr(a, "disrupted_quantity", None) or getattr(a, "production_loss_tonnes", 0.0) or 0.0)
                for a in agri
            )
        if getattr(bundle, "total_estimated_loss_inr", None) is not None:
            summary["direct_economic_loss_inr"] = bundle.total_estimated_loss_inr
        elif getattr(bundle, "economic_loss_evaluations", None):
            summary["direct_economic_loss_inr"] = sum(
                getattr(e, "estimated_loss_inr", 0.0) or 0.0 for e in bundle.economic_loss_evaluations
            )
        return summary

    def _extract_impact_conditions(self, bundle: Any) -> Dict[str, Any]:
        """Extracts boolean trigger conditions from impact bundle."""
        conds: Dict[str, Any] = {}
        assessments = getattr(bundle, "assessments", []) or []

        roads = getattr(bundle, "road_impacts", None) or [a for a in assessments if getattr(a, "entity_type", "").upper() == "ROAD"]
        hospitals = getattr(bundle, "hospital_impacts", None) or [a for a in assessments if getattr(a, "entity_type", "").upper() == "HOSPITAL"]
        schools = getattr(bundle, "school_impacts", None) or [a for a in assessments if getattr(a, "entity_type", "").upper() == "SCHOOL"]
        agri = getattr(bundle, "agricultural_impacts", None) or [a for a in assessments if getattr(a, "entity_type", "").upper() == "AGRICULTURE"]

        if roads:
            conds["road_disrupted"] = any(
                getattr(r, "damage_state", None) in [DamageState.MODERATE, DamageState.MAJOR, DamageState.SEVERE]
                for r in roads
            )
        if hospitals:
            conds["hospital_strain"] = any(
                getattr(h, "damage_state", None) in [DamageState.MODERATE, DamageState.MAJOR, DamageState.SEVERE]
                or ((getattr(h, "disrupted_quantity", 0.0) or getattr(h, "inpatient_beds_at_risk", 0.0) or getattr(h, "details", {}).get("inpatient_beds_at_risk", 0.0) or 0.0) > 0)
                for h in hospitals
            )
        if schools:
            conds["shelter_suitable"] = any(
                getattr(s, "shelter_suitability_flag", False) or getattr(s, "details", {}).get("shelter_suitability_flag", False)
                for s in schools
            )
        if agri:
            for a in agri:
                c_stage = getattr(a, "crop_growth_stage", None) or getattr(a, "details", {}).get("crop_growth_stage", None)
                if c_stage and str(c_stage).upper() == "FLOWERING":
                    conds["crop_stage"] = "FLOWERING"
                    break
        return conds

    def _generate_recommendations(
        self,
        eligible_rules: List[DecisionRule],
        primary_warning: Optional[OfficialWarningInfo],
        has_official_evacuation: bool,
        has_official_closure: bool,
        evidence_quality: str,
        geography: str,
        impact_conds: Dict[str, Any],
        risk_tier: Optional[str] = None,
        active_warnings: Optional[List[OfficialWarningInfo]] = None,
    ) -> List[ActionRecommendation]:
        """Generates validated, claim-governed ActionRecommendations."""
        recommendations: List[ActionRecommendation] = []
        warnings_pool = active_warnings if active_warnings else ([primary_warning] if primary_warning else [])

        for rule in eligible_rules:
            # 1. Official Warning Bulletin Pass-Through
            if rule.rule_id == "DEC-RULE-OFFICIAL-WARN-001" and primary_warning is not None:
                headline = f"Official {primary_warning.authority} {primary_warning.warning_level} Warning"
                desc = primary_warning.instruction or primary_warning.headline or primary_warning.description
                if not desc:
                    desc = f"Official weather warning in effect for {geography}. Comply with local disaster management advisories."
                act = ActionRecommendation(
                    action_id=f"ACT-OFFICIAL-{primary_warning.alert_id}",
                    action_code="OFFICIAL_WARNING_NOTICE",
                    category=ActionCategory.OFFICIAL_DIRECTIVE,
                    source=ActionSource.OFFICIAL_SOURCE,
                    priority=PriorityClass.HIGH,
                    headline=headline,
                    description=desc,
                    human_verification_required=False,
                    verification_reason=None,
                    claim_id=rule.claim_id,
                    sector="general",
                )
                self.claim_validator.validate_action_recommendation(
                    act,
                    has_official_evacuation=has_official_evacuation,
                    has_official_closure=has_official_closure,
                    quality_state=evidence_quality,
                )
                recommendations.append(act)

            # 2. Official Evacuation Directive Pass-Through
            elif rule.rule_id == "DEC-RULE-OFFICIAL-EVAC-001" and has_official_evacuation:
                evac_warning = next((w for w in warnings_pool if w and w.evacuation_ordered), None)
                auth = evac_warning.authority if evac_warning else "District Emergency Authority"
                act = ActionRecommendation(
                    action_id="ACT-EVAC-OFFICIAL",
                    action_code="OFFICIAL_EVACUATION_DIRECTIVE",
                    category=ActionCategory.OFFICIAL_DIRECTIVE,
                    source=ActionSource.OFFICIAL_SOURCE,
                    priority=PriorityClass.IMMEDIATE_ATTENTION,
                    headline=f"Official Evacuation Directive Issued by {auth}",
                    description=(
                        f"Statutory evacuation decree in effect for designated vulnerable zones in {geography}. "
                        "Follow official transport and designated shelter route instructions immediately."
                    ),
                    human_verification_required=False,
                    verification_reason=None,
                    claim_id=rule.claim_id,
                    sector="general",
                )
                self.claim_validator.validate_action_recommendation(
                    act,
                    has_official_evacuation=has_official_evacuation,
                    has_official_closure=has_official_closure,
                    quality_state=evidence_quality,
                )
                recommendations.append(act)

            # 3. Road Inundation Caution & Verification (Never asserts official closure)
            elif rule.rule_id == "DEC-RULE-ROAD-VERIFY-001":
                act = ActionRecommendation(
                    action_id="ACT-ROAD-VERIFY-001",
                    action_code="VERIFY_ROUTE_CLEARANCE",
                    category=ActionCategory.VERIFY,
                    source=ActionSource.VAYUBODHAK_PROTOTYPE,
                    priority=PriorityClass.HIGH,
                    headline="Potential Road Corridor Waterlogging Detected",
                    description=(
                        f"Potential surface inundation modeled on transportation corridors in {geography}. "
                        "Official road closure: NOT CONFIRMED. "
                        "Exercise travel caution and check local traffic police bulletins for verified route passability."
                    ),
                    human_verification_required=True,
                    verification_reason="Physical route clearance and official closure status must be confirmed via local police/traffic authorities",
                    claim_id=rule.claim_id,
                    sector="infrastructure",
                )
                self.claim_validator.validate_action_recommendation(
                    act,
                    has_official_evacuation=has_official_evacuation,
                    has_official_closure=has_official_closure,
                    quality_state=evidence_quality,
                )
                recommendations.append(act)

            # 4. Healthcare Lifeline Continuity Review
            elif rule.rule_id == "DEC-RULE-HOSP-STRAIN-001":
                act = ActionRecommendation(
                    action_id="ACT-HOSP-STRAIN-001",
                    action_code="COORDINATE_HOSPITAL_LIFELINE",
                    category=ActionCategory.COORDINATE,
                    source=ActionSource.RESEARCH_SUPPORTED,
                    priority=PriorityClass.HIGH,
                    headline="Healthcare Lifeline Continuity Review Recommended",
                    description=(
                        f"Surrounding access corridor waterlogging may strain inpatient capacity in {geography}. "
                        "Coordinate auxiliary power backups and verify emergency ambulance access routes."
                    ),
                    human_verification_required=True,
                    verification_reason="Facility operational response requires hospital administration review",
                    claim_id=rule.claim_id,
                    sector="healthcare",
                )
                self.claim_validator.validate_action_recommendation(
                    act,
                    has_official_evacuation=has_official_evacuation,
                    has_official_closure=has_official_closure,
                    quality_state=evidence_quality,
                )
                recommendations.append(act)

            # 5. Educational Shelter Suitability Review (Never designates official shelter)
            elif rule.rule_id == "DEC-RULE-SCHL-SHELTER-001":
                act = ActionRecommendation(
                    action_id="ACT-SCHL-SHELTER-001",
                    action_code="REVIEW_SHELTER_SUITABILITY",
                    category=ActionCategory.VERIFY,
                    source=ActionSource.VAYUBODHAK_PROTOTYPE,
                    priority=PriorityClass.ROUTINE,
                    headline="Preliminary Dual-Use Emergency Shelter Suitability Flagged",
                    description=(
                        f"Educational facilities in {geography} flagged as potentially suitable for dual-use emergency shelter. "
                        "PROTOTYPE_SUITABILITY_ASSESSMENT only; does NOT designate an official emergency shelter without municipal or district administration order."
                    ),
                    human_verification_required=True,
                    verification_reason="Official shelter activation requires municipal structural certification and administrative order",
                    claim_id=rule.claim_id,
                    sector="education",
                )
                self.claim_validator.validate_action_recommendation(
                    act,
                    has_official_evacuation=has_official_evacuation,
                    has_official_closure=has_official_closure,
                    quality_state=evidence_quality,
                )
                recommendations.append(act)

            # 6. Agricultural Flowering Preparedness
            elif rule.rule_id == "DEC-RULE-AGRI-PREPARE-001":
                act = ActionRecommendation(
                    action_id="ACT-AGRI-FLOWERING-001",
                    action_code="PREPARE_CROP_PROTECTION",
                    category=ActionCategory.PREPARE,
                    source=ActionSource.RESEARCH_SUPPORTED,
                    priority=PriorityClass.HIGH,
                    headline="Crop Flowering Stage Stress Mitigation Advisory",
                    description=(
                        f"Standing crops in {geography} are in the sensitive flowering stage. "
                        "Ensure field drainage channels are cleared to prevent root submergence and maintain light irrigation."
                    ),
                    human_verification_required=False,
                    verification_reason=None,
                    claim_id=rule.claim_id,
                    sector="agriculture",
                )
                self.claim_validator.validate_action_recommendation(
                    act,
                    has_official_evacuation=has_official_evacuation,
                    has_official_closure=has_official_closure,
                    quality_state=evidence_quality,
                )
                recommendations.append(act)

            # 7. Multi-Sector Cyclone Preparedness
            elif rule.rule_id == "DEC-RULE-CYCLONE-PREPARE-001":
                act = ActionRecommendation(
                    action_id="ACT-CYCLONE-PREPARE-001",
                    action_code="PREPARE_CYCLONE_SAFETY",
                    category=ActionCategory.PREPARE,
                    source=ActionSource.RESEARCH_SUPPORTED,
                    priority=PriorityClass.HIGH,
                    headline="Severe Cyclonic Weather Preparedness Advisory",
                    description=(
                        f"Secure loose rooftop sheets, outdoor structures, and store emergency dry rations in {geography}. "
                        "Fishermen strictly advised to avoid venturing into coastal waters."
                    ),
                    human_verification_required=True,
                    verification_reason="Civil preparedness adherence requires local community coordination",
                    claim_id=rule.claim_id,
                    sector="general",
                )
                self.claim_validator.validate_action_recommendation(
                    act,
                    has_official_evacuation=has_official_evacuation,
                    has_official_closure=has_official_closure,
                    quality_state=evidence_quality,
                )
                recommendations.append(act)

            # 8. Extreme Heat Protection
            elif rule.rule_id == "DEC-RULE-HEATWAVE-PROTECT-001":
                act = ActionRecommendation(
                    action_id="ACT-HEAT-PROTECT-001",
                    action_code="PROTECT_HEAT_ILLNESS",
                    category=ActionCategory.PROTECT,
                    source=ActionSource.RESEARCH_SUPPORTED,
                    priority=PriorityClass.HIGH,
                    headline="Extreme Heat Illness Protection Advisory",
                    description=(
                        f"Avoid direct sun exposure between 12:00 and 15:00 IST in {geography}. "
                        "Ensure continuous hydration and shade for vulnerable family members and livestock."
                    ),
                    human_verification_required=False,
                    verification_reason=None,
                    claim_id=rule.claim_id,
                    sector="general",
                )
                self.claim_validator.validate_action_recommendation(
                    act,
                    has_official_evacuation=has_official_evacuation,
                    has_official_closure=has_official_closure,
                    quality_state=evidence_quality,
                )
                recommendations.append(act)

            # 9. Insufficient Evidence Fallback
            elif rule.rule_id == "DEC-RULE-INSUFFICIENT-EVID-001":
                act = ActionRecommendation(
                    action_id="ACT-INSUFFICIENT-EVID-001",
                    action_code="MONITOR_INSUFFICIENT_EVIDENCE",
                    category=ActionCategory.MONITOR,
                    source=ActionSource.OFFICIAL_SOURCE,
                    priority=PriorityClass.INFORMATIONAL,
                    headline="Observational Evidence Incomplete or Stale",
                    description=(
                        f"Meteorological or hazard observations for {geography} are currently incomplete or stale. "
                        "Maintain monitoring of official IMD/NDMA bulletins before undertaking safety-critical actions."
                    ),
                    human_verification_required=False,
                    verification_reason=None,
                    claim_id=rule.claim_id,
                    sector="general",
                )
                self.claim_validator.validate_action_recommendation(
                    act,
                    has_official_evacuation=has_official_evacuation,
                    has_official_closure=has_official_closure,
                    quality_state=evidence_quality,
                )
                recommendations.append(act)

            # 10. Risk Mapping: Moderate Risk to Monitoring
            elif rule.rule_id == "DEC-RULE-RISK-MODERATE-MONITOR-001":
                act = ActionRecommendation(
                    action_id="ACT-RISK-MODERATE-001",
                    action_code="MONITOR_MODERATE_RISK",
                    category=ActionCategory.MONITOR,
                    source=ActionSource.VAYUBODHAK_PROTOTYPE,
                    priority=PriorityClass.ROUTINE,
                    headline="Moderate Quantitative Risk: Active Monitoring Recommended",
                    description=(
                        f"Composite quantitative risk in {geography} evaluated as Moderate. "
                        "Maintain situational awareness and monitor local weather updates."
                    ),
                    human_verification_required=False,
                    verification_reason=None,
                    claim_id=rule.claim_id,
                    sector="general",
                )
                self.claim_validator.validate_action_recommendation(
                    act,
                    has_official_evacuation=has_official_evacuation,
                    has_official_closure=has_official_closure,
                    quality_state=evidence_quality,
                )
                recommendations.append(act)

            # 11. Risk Mapping: High / Very High Risk to Preparedness
            elif rule.rule_id == "DEC-RULE-RISK-HIGH-PREPARE-001":
                act = ActionRecommendation(
                    action_id="ACT-RISK-HIGH-001",
                    action_code="PREPARE_HIGH_RISK",
                    category=ActionCategory.PREPARE,
                    source=ActionSource.VAYUBODHAK_PROTOTYPE,
                    priority=PriorityClass.HIGH,
                    headline="High Quantitative Risk: Precautionary Preparedness Recommended",
                    description=(
                        f"Composite quantitative risk in {geography} evaluated as High / Very High. "
                        "Implement precautionary protective measures and review emergency readiness."
                    ),
                    human_verification_required=True,
                    verification_reason="Precautionary escalation requires field operational confirmation",
                    claim_id=rule.claim_id,
                    sector="general",
                )
                self.claim_validator.validate_action_recommendation(
                    act,
                    has_official_evacuation=has_official_evacuation,
                    has_official_closure=has_official_closure,
                    quality_state=evidence_quality,
                )
                recommendations.append(act)

        return recommendations

    def _build_decision_conditions(
        self,
        hazard_type: str,
        hazard_state: str,
        evidence_quality: str,
        has_official_warning: bool,
        impact_conds: Dict[str, Any],
        decision_state: DecisionState,
        risk_tier: Optional[str] = None,
    ) -> List[str]:
        """Constructs human-readable list of validated conditions."""
        conds = [
            f"Evidence Quality: {evidence_quality}",
            f"Hazard State: {hazard_state} ({hazard_type})",
            f"Official Warning Present: {has_official_warning}",
            f"Governing Decision State: {decision_state.value}",
        ]
        if risk_tier:
            conds.append(f"Quantitative Risk Tier: {risk_tier}")
        if impact_conds.get("road_disrupted"):
            conds.append("Road Inundation: Potential disruption trigger exceeded (Official closure = NOT CONFIRMED)")
        if impact_conds.get("hospital_strain"):
            conds.append("Healthcare Facility: Access corridor strain detected")
        if impact_conds.get("shelter_suitable"):
            conds.append("Educational Facility: Preliminary shelter suitability identified (Dual-use prototype assessment)")
        if impact_conds.get("crop_stage") == "FLOWERING":
            conds.append("Agricultural Crop: Anthesis/flowering sensitivity window active")
        return conds

    def _detect_decision_change(
        self,
        current_id: str,
        current_state: DecisionState,
        previous_decision: DecisionPackage,
        now_iso: str,
    ) -> DecisionChangeRecord:
        """Compares current state to previous decision and determines structured transition reason."""
        prev_state = previous_decision.decision.decision_status
        prev_id = previous_decision.decision_id

        if prev_state == current_state:
            reason_code = ChangeReasonCode.OFFICIAL_WARNING_UPDATED
            details = "Decision state remains unchanged; telemetry re-evaluated."
        elif current_state == DecisionState.OFFICIAL_ACTION_AVAILABLE and prev_state != DecisionState.OFFICIAL_ACTION_AVAILABLE:
            reason_code = ChangeReasonCode.OFFICIAL_WARNING_ISSUED
            details = "Transitioned to OFFICIAL_ACTION_AVAILABLE due to newly issued official bulletin."
        elif current_state == DecisionState.PREPARE and prev_state in [DecisionState.NO_SIGNAL, DecisionState.MONITOR]:
            reason_code = ChangeReasonCode.HAZARD_ESCALATED
            details = "Transitioned to PREPARE due to escalated hazard severity or increased potential impact."
        elif current_state == DecisionState.INSUFFICIENT_EVIDENCE:
            reason_code = ChangeReasonCode.EVIDENCE_EXPIRED
            details = "Transitioned to INSUFFICIENT_EVIDENCE due to stale or missing observational inputs."
        elif current_state == DecisionState.REVIEW_REQUIRED:
            reason_code = ChangeReasonCode.CONFLICT_DETECTED
            details = "Transitioned to REVIEW_REQUIRED due to conflicting evidence or stale rapid hazard observation."
        else:
            reason_code = ChangeReasonCode.INITIAL_EVALUATION
            details = f"Transitioned from {prev_state.value} to {current_state.value} based on updated evidence."

        return DecisionChangeRecord(
            decision_id=current_id,
            previous_decision_id=prev_id,
            previous_state=prev_state,
            new_state=current_state,
            reason_code=reason_code,
            reason_details=details,
            changed_at_iso=now_iso,
        )

    def _calculate_provenance_hash(
        self,
        decision_id: str,
        version: int,
        hazard_id: Optional[str],
        exposure_id: Optional[str],
        vulnerability_id: Optional[str],
        risk_id: Optional[str],
        impact_id: Optional[str],
        method_ids: List[str],
        rule_version: str,
        decision_state: str,
        action_categories: List[str],
        official_warning_ids: List[str],
        claim_ids: List[str],
    ) -> str:
        """Computes cryptographic SHA-256 hash linking complete upstream execution trace."""
        payload = {
            "decision_id": decision_id,
            "version": version,
            "hazard_id": hazard_id or "NONE",
            "exposure_id": exposure_id or "NONE",
            "vulnerability_id": vulnerability_id or "NONE",
            "risk_id": risk_id or "NONE",
            "impact_id": impact_id or "NONE",
            "rule_ids": sorted(method_ids),
            "rule_version": rule_version,
            "decision_state": decision_state,
            "action_categories": sorted(action_categories),
            "official_warning_ids": sorted(official_warning_ids),
            "claim_ids": sorted(claim_ids),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _build_nirnay_card(
        self,
        decision_context: DecisionContext,
        primary_warning: Optional[OfficialWarningInfo],
        recommendations: List[ActionRecommendation],
        geography: str,
        now_iso: str,
        scheduled_warnings: Optional[List[OfficialWarningInfo]] = None,
    ) -> NirnayCard:
        """Constructs canonical presentation NirnayCard supporting both Phase 8 and backward-compatible fields."""
        verdict = DecisionOutcome.MONITOR
        severity = SeverityLevel.LOW
        if decision_context.decision_status == DecisionState.OFFICIAL_ACTION_AVAILABLE:
            verdict = DecisionOutcome.POSTPONE
            severity = SeverityLevel.HIGH
        elif decision_context.decision_status == DecisionState.PREPARE:
            verdict = DecisionOutcome.POSTPONE
            severity = SeverityLevel.HIGH
        elif decision_context.decision_status == DecisionState.ACTION_RECOMMENDED:
            verdict = DecisionOutcome.PROCEED_WITH_CAUTION
            severity = SeverityLevel.MODERATE
        elif decision_context.decision_status == DecisionState.INSUFFICIENT_EVIDENCE:
            verdict = DecisionOutcome.INSUFFICIENT_DATA
            severity = SeverityLevel.LOW

        top_action_str = recommendations[0].headline if recommendations else "Maintain monitoring of official bulletins."

        why_bullets = list(decision_context.decision_conditions)
        if primary_warning:
            why_bullets.append(f"Official Warning Active: {primary_warning.headline} ({primary_warning.authority})")
        else:
            why_bullets.append("No active official government warning bulletin detected")

        if scheduled_warnings:
            for sw in scheduled_warnings:
                why_bullets.append(f"Scheduled Warning: {sw.headline} ({sw.authority}) valid from {sw.valid_from_iso} (Not Active)")

        verification_items = [
            f"{a.headline}: {a.verification_reason}" for a in recommendations if a.human_verification_required and a.verification_reason
        ]

        # Explicit separation in situation dictionary
        situation_dict: Dict[str, Any] = {
            "geography": geography,
            "hazard_type": decision_context.hazard_type,
            "hazard_state": decision_context.hazard_state,
            "decision_state": decision_context.decision_status.value,
            "assessment_time": now_iso,
        }
        if primary_warning:
            situation_dict["official_information"] = {
                "authority": primary_warning.authority,
                "warning_level": primary_warning.warning_level,
                "official_text": primary_warning.official_text or primary_warning.instruction or primary_warning.description,
                "system_summary": primary_warning.system_summary,
                "translated_text": primary_warning.translated_text,
                "authoritative_field": "official_text",
            }

        return NirnayCard(
            question=f"Operational decision assessment for {geography}",
            verdict=verdict,
            severity=severity,
            recommended_action=top_action_str,
            action_window={"status": "unavailable", "reason": "Disaster decision support"},
            confidence=ConfidenceLevel.HIGH if decision_context.data_coverage >= 0.8 else ConfidenceLevel.MEDIUM,
            uncertainty=decision_context.uncertainty,
            why=why_bullets,
            impact=decision_context.impact_summary,
            alternatives=["Check local district disaster management bulletins", "Verify field route clearance"],
            evidence={
                "evidence_quality": decision_context.evidence_quality,
                "data_coverage": decision_context.data_coverage,
                "staleness_state": decision_context.staleness_state,
                "provenance_hash": decision_context.provenance_id,
            },
            ledger=None,
            explanation=None,
            # Phase 8 Structured Sections
            situation=situation_dict,
            affected_scope={
                "geography": geography,
                "spatial_resolution": decision_context.spatial_resolution,
            },
            risk_context={
                "risk_level": decision_context.risk_level or "UNSPECIFIED",
                "risk_id": decision_context.risk_id,
            },
            impact_context=decision_context.impact_summary,
            official_information=primary_warning,
            recommended_actions=recommendations,
            verification_required=verification_items,
            limitations=[
                "Decision support heuristic; does not replace statutory disaster authorities",
                "Consequence metrics are prototype approximations",
            ],
            provenance={
                "provenance_id": decision_context.provenance_id,
                "version": decision_context.version,
                "method_ids": decision_context.method_ids,
                "claim_ids": decision_context.claim_ids,
            },
            timestamp=now_iso,
            decision_state=decision_context.decision_status,
            human_verification_required=decision_context.human_verification_required,
        )


# Canonical singleton
nirnay_engine = NirnayEngine()

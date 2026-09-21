"""Decision Rule Registry for VAYUBODHAK Phase 8 — Decision Support & Nirnay Engine.

Maintains an immutable, version-controlled repository of deterministic decision rules.
Enforces strict parameter provenance, source attribution, and safety boundaries.

Core Invariants:
1. Zero client-side rule injection; no dynamic eval() or user-supplied formulas.
2. Every rule is classified as SOURCE_DEFINED, RESEARCH_SUPPORTED, or VAYUBODHAK_PROTOTYPE.
3. Every rule is linked to a Phase 2A Claim Gate claim ID.
4. Rules are activated only when input conditions, quality states, and official source requirements match.
5. Every Risk → Decision mapping is explicitly classified and carries full metadata.
"""

from typing import Any, Dict, List, Optional
from app.decision.models import (
    ActionCategory,
    DecisionRule,
    DecisionState,
    PriorityClass,
)


class DecisionRuleRegistry:
    """Immutable registry of governing decision rules."""

    def __init__(self) -> None:
        self._rules: Dict[str, DecisionRule] = {}
        self._initialize_canonical_rules()

    def _initialize_canonical_rules(self) -> None:
        """Populates the canonical national and research-grounded decision rules."""
        canonical_rules = [
            # 1. Official Warning Bulletin Pass-Through
            DecisionRule(
                rule_id="DEC-RULE-OFFICIAL-WARN-001",
                rule_name="Official Warning Bulletin Pass-Through",
                hazard_types=["HEAVY_RAINFALL", "FLOOD", "CYCLONE", "HEATWAVE", "COLDWAVE", "THUNDERSTORM", "ALL"],
                required_hazard_states=["ALL"],
                required_impact_conditions={},
                required_exposure_conditions={},
                required_data_quality=["VALID"],
                official_source_requirement="OFFICIAL",
                action_category=ActionCategory.OFFICIAL_DIRECTIVE,
                priority=PriorityClass.HIGH,
                method_version="1.0.0",
                rule_version="1.0.0",
                source_basis="IMD NWFC / NDMA SACHET Alert Protocols",
                classification="SOURCE_DEFINED",
                claim_id="CLAIM-DEC-OFFICIAL-001",
                input_conditions={"official_warning": True},
                decision_state=DecisionState.OFFICIAL_ACTION_AVAILABLE,
                human_verification_required=False,
                limitations=[
                    "Pass-through of official alert bulletins without mutating authority text",
                    "Validity bounds (valid_from, valid_to) strictly enforced",
                ],
                enabled=True,
            ),
            # 2. Official Statutory Evacuation Order Pass-Through
            DecisionRule(
                rule_id="DEC-RULE-OFFICIAL-EVAC-001",
                rule_name="Official Statutory Evacuation Order Pass-Through",
                hazard_types=["FLOOD", "CYCLONE", "LANDSLIDE", "ALL"],
                required_hazard_states=["ALL"],
                required_impact_conditions={},
                required_exposure_conditions={},
                required_data_quality=["VALID"],
                official_source_requirement="OFFICIAL_EVACUATION",
                action_category=ActionCategory.OFFICIAL_DIRECTIVE,
                priority=PriorityClass.IMMEDIATE_ATTENTION,
                method_version="1.0.0",
                rule_version="1.0.0",
                source_basis="Statutory District Administration Order under DM Act 2005",
                classification="SOURCE_DEFINED",
                claim_id="CLAIM-DEC-EVAC-001",
                input_conditions={"official_evacuation_ordered": True},
                decision_state=DecisionState.OFFICIAL_ACTION_AVAILABLE,
                human_verification_required=False,
                limitations=[
                    "Strict pass-through of verified statutory executive orders only",
                    "VAYUBODHAK never autonomously orders emergency evacuation",
                ],
                enabled=True,
            ),
            # 3. Road Inundation Local Verification & Travel Caution
            DecisionRule(
                rule_id="DEC-RULE-ROAD-VERIFY-001",
                rule_name="Road Corridor Inundation Verification & Caution",
                hazard_types=["HEAVY_RAINFALL", "FLOOD", "CYCLONE", "ALL"],
                required_hazard_states=["ALL"],
                required_impact_conditions={"road_disrupted": True},
                required_exposure_conditions={},
                required_data_quality=["VALID"],
                official_source_requirement=None,
                action_category=ActionCategory.VERIFY,
                priority=PriorityClass.HIGH,
                method_version="1.0.0",
                rule_version="1.0.0",
                source_basis="IRC:SP:42 & IRC:SP:50 Rural Road Drainage & Trafficability Guidelines",
                classification="VAYUBODHAK_PROTOTYPE",
                claim_id="CLAIM-DEC-ROAD-001",
                input_conditions={"road_disrupted": True},
                decision_state=DecisionState.ACTION_RECOMMENDED,
                human_verification_required=True,
                limitations=[
                    "Modeled surface disruption is an uncalibrated scenario approximation",
                    "Official road closure requires confirmation from local traffic police/highway authorities",
                ],
                enabled=True,
            ),
            # 4. Healthcare Facility Lifeline Continuity & Bed Strain Review
            DecisionRule(
                rule_id="DEC-RULE-HOSP-STRAIN-001",
                rule_name="Healthcare Facility Operational Continuity Review",
                hazard_types=["FLOOD", "CYCLONE", "HEATWAVE", "ALL"],
                required_hazard_states=["ALL"],
                required_impact_conditions={"hospital_strain": True},
                required_exposure_conditions={},
                required_data_quality=["VALID"],
                official_source_requirement=None,
                action_category=ActionCategory.COORDINATE,
                priority=PriorityClass.HIGH,
                method_version="1.0.0",
                rule_version="1.0.0",
                source_basis="WHO Hospital Safety Index (2015) & NDMA Lifeline Continuity Principles",
                classification="RESEARCH_SUPPORTED",
                claim_id="CLAIM-DEC-HOSP-001",
                input_conditions={"hospital_strain": True},
                decision_state=DecisionState.ACTION_RECOMMENDED,
                human_verification_required=True,
                limitations=[
                    "Access corridor strain is evaluated from spatial proximity heuristics",
                    "Internal medical and auxiliary generator deployment remains facility prerogative",
                ],
                enabled=True,
            ),
            # 5. Educational Institution Emergency Shelter Suitability Review
            DecisionRule(
                rule_id="DEC-RULE-SCHL-SHELTER-001",
                rule_name="Educational Institution Emergency Shelter Suitability Review",
                hazard_types=["FLOOD", "CYCLONE", "ALL"],
                required_hazard_states=["ALL"],
                required_impact_conditions={"shelter_suitable": True},
                required_exposure_conditions={},
                required_data_quality=["VALID"],
                official_source_requirement=None,
                action_category=ActionCategory.VERIFY,
                priority=PriorityClass.ROUTINE,
                method_version="1.0.0",
                rule_version="1.0.0",
                source_basis="NDMA National School Safety Policy (2016) Dual-Use Shelter Concept",
                classification="VAYUBODHAK_PROTOTYPE",
                claim_id="CLAIM-DEC-SCHL-001",
                input_conditions={"shelter_suitable": True},
                decision_state=DecisionState.ACTION_RECOMMENDED,
                human_verification_required=True,
                limitations=[
                    "Dual-use suitability is an indicative municipal asset evaluation",
                    "Does NOT designate an official emergency shelter without district administration notification",
                ],
                enabled=True,
            ),
            # 6. Crop Flowering Stage Stress Preparedness Advisory
            DecisionRule(
                rule_id="DEC-RULE-AGRI-PREPARE-001",
                rule_name="Crop Flowering Stage Stress Preparedness Advisory",
                hazard_types=["HEATWAVE", "HEAVY_RAINFALL", "FLOOD"],
                required_hazard_states=["WARNING", "SEVERE", "EXTREME"],
                required_impact_conditions={"crop_stage": "FLOWERING"},
                required_exposure_conditions={},
                required_data_quality=["VALID"],
                official_source_requirement=None,
                action_category=ActionCategory.PREPARE,
                priority=PriorityClass.HIGH,
                method_version="1.0.0",
                rule_version="1.0.0",
                source_basis="ICAR Agrometeorological Advisory Guidelines & FAO-56 / FAO-66",
                classification="RESEARCH_SUPPORTED",
                claim_id="CLAIM-DEC-AGRI-001",
                input_conditions={"crop_stage": "FLOWERING"},
                decision_state=DecisionState.PREPARE,
                human_verification_required=False,
                limitations=[
                    "Agronomic guidance based on anthesis sensitivity; field drainage depends on local topography",
                ],
                enabled=True,
            ),
            # 7. Severe Cyclonic Weather Multi-Sector Preparedness
            DecisionRule(
                rule_id="DEC-RULE-CYCLONE-PREPARE-001",
                rule_name="Severe Cyclonic Weather Multi-Sector Preparedness",
                hazard_types=["CYCLONE"],
                required_hazard_states=["WARNING", "SEVERE", "EXTREME"],
                required_impact_conditions={},
                required_exposure_conditions={},
                required_data_quality=["VALID"],
                official_source_requirement=None,
                action_category=ActionCategory.PREPARE,
                priority=PriorityClass.HIGH,
                method_version="1.0.0",
                rule_version="1.0.0",
                source_basis="NDMA Cyclone Guidelines & IMD Cyclone Standard Operating Procedures",
                classification="RESEARCH_SUPPORTED",
                claim_id="CLAIM-DEC-CYCLONE-001",
                input_conditions={"hazard_type": "CYCLONE", "hazard_state": ["WARNING", "SEVERE", "EXTREME"]},
                decision_state=DecisionState.PREPARE,
                human_verification_required=True,
                limitations=[
                    "Community preparedness advisory; adherence subject to district administration guidelines",
                ],
                enabled=True,
            ),
            # 8. Extreme Heat Public Health Protection Advisory
            DecisionRule(
                rule_id="DEC-RULE-HEATWAVE-PROTECT-001",
                rule_name="Extreme Heat Public Health Protection Advisory",
                hazard_types=["HEATWAVE"],
                required_hazard_states=["WARNING", "SEVERE", "EXTREME"],
                required_impact_conditions={},
                required_exposure_conditions={},
                required_data_quality=["VALID"],
                official_source_requirement=None,
                action_category=ActionCategory.PROTECT,
                priority=PriorityClass.HIGH,
                method_version="1.0.0",
                rule_version="1.0.0",
                source_basis="NDMA National Heat Action Plan Guidelines & IMD Heatwave Warning Matrix",
                classification="RESEARCH_SUPPORTED",
                claim_id="CLAIM-DEC-HEAT-001",
                input_conditions={"hazard_type": "HEATWAVE", "hazard_state": ["WARNING", "SEVERE", "EXTREME"]},
                decision_state=DecisionState.PREPARE,
                human_verification_required=False,
                limitations=[
                    "Public health behavioral guidance; not an individualized medical treatment plan",
                ],
                enabled=True,
            ),
            # 9. Insufficient Evidence Safety Fallback
            DecisionRule(
                rule_id="DEC-RULE-INSUFFICIENT-EVID-001",
                rule_name="Insufficient Evidence Safety Fallback",
                hazard_types=["ALL", "HEAVY_RAINFALL", "FLOOD", "CYCLONE", "HEATWAVE"],
                required_hazard_states=["ALL", "NONE", "WATCH", "WARNING", "SEVERE", "EXTREME"],
                required_impact_conditions={},
                required_exposure_conditions={},
                required_data_quality=["MISSING", "STALE", "INVALID", "CONFLICT", "INSUFFICIENT_EVIDENCE"],
                official_source_requirement=None,
                action_category=ActionCategory.MONITOR,
                priority=PriorityClass.INFORMATIONAL,
                method_version="1.0.0",
                rule_version="1.0.0",
                source_basis="WMO-No. 1150 Precautionary Disaster Risk Principle & VAYUBODHAK Safety Governance",
                classification="SOURCE_DEFINED",
                claim_id="CLAIM-DEC-INSUFFICIENT-001",
                input_conditions={"quality_state": ["MISSING", "STALE", "INVALID", "CONFLICT", "INSUFFICIENT_EVIDENCE"]},
                decision_state=DecisionState.INSUFFICIENT_EVIDENCE,
                human_verification_required=False,
                limitations=[
                    "Precautionary principle strictly blocks assertions of zero danger or safety when data is missing",
                ],
                enabled=True,
            ),
            # 10. Risk Mapping: Moderate Quantitative Risk to Operational Monitoring
            DecisionRule(
                rule_id="DEC-RULE-RISK-MODERATE-MONITOR-001",
                rule_name="Moderate Quantitative Risk to Operational Monitoring Mapping",
                hazard_types=["ALL"],
                required_hazard_states=["ALL", "WATCH", "WARNING"],
                required_impact_conditions={},
                required_exposure_conditions={},
                required_data_quality=["VALID"],
                official_source_requirement=None,
                action_category=ActionCategory.MONITOR,
                priority=PriorityClass.ROUTINE,
                method_version="1.0.0",
                rule_version="1.0.0",
                source_basis="UNDRR / NDMA Risk Assessment & Mitigation Principles",
                classification="VAYUBODHAK_PROTOTYPE",
                claim_id="CLAIM-DEC-RISK-MAP-001",
                input_conditions={"risk_tier": "MODERATE"},
                decision_state=DecisionState.MONITOR,
                human_verification_required=False,
                limitations=[
                    "Heuristic mapping from Phase 6 composite risk index to MONITOR state",
                    "Institutional guidelines define risk concepts but do not specify automated software transitions",
                ],
                enabled=True,
            ),
            # 11. Risk Mapping: High & Very High Quantitative Risk to Preparedness
            DecisionRule(
                rule_id="DEC-RULE-RISK-HIGH-PREPARE-001",
                rule_name="High and Very High Quantitative Risk to Preparedness Mapping",
                hazard_types=["ALL"],
                required_hazard_states=["ALL", "WARNING", "SEVERE", "EXTREME"],
                required_impact_conditions={},
                required_exposure_conditions={},
                required_data_quality=["VALID"],
                official_source_requirement=None,
                action_category=ActionCategory.PREPARE,
                priority=PriorityClass.HIGH,
                method_version="1.0.0",
                rule_version="1.0.0",
                source_basis="UNDRR / NDMA Risk Assessment & Mitigation Principles",
                classification="VAYUBODHAK_PROTOTYPE",
                claim_id="CLAIM-DEC-RISK-MAP-002",
                input_conditions={"risk_tier": ["HIGH", "VERY_HIGH"]},
                decision_state=DecisionState.PREPARE,
                human_verification_required=True,
                limitations=[
                    "Heuristic mapping from Phase 6 high risk index to PREPARE state",
                    "Institutional guidelines define risk concepts but do not specify automated software transitions",
                ],
                enabled=True,
            ),
        ]

        for rule in canonical_rules:
            self._rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> Optional[DecisionRule]:
        """Retrieves a rule by ID."""
        return self._rules.get(rule_id)

    def list_rules(self, enabled_only: bool = True) -> List[DecisionRule]:
        """Returns all registered decision rules."""
        if enabled_only:
            return [r for r in self._rules.values() if r.enabled]
        return list(self._rules.values())

    def find_eligible_rules(
        self,
        hazard_type: str,
        hazard_state: str,
        quality_state: str,
        has_official_source: bool = False,
        has_official_evacuation: bool = False,
        impact_conditions: Optional[Dict[str, Any]] = None,
        risk_tier: Optional[str] = None,
    ) -> List[DecisionRule]:
        """Finds all active rules whose triggering preconditions are fully satisfied.
        
        Evaluates:
        - Hazard type match ('ALL' or specific type)
        - Hazard severity match ('ALL' or specific state)
        - Data quality requirement match
        - Official source presence match
        - Impact condition preconditions
        - Risk tier match (for risk mapping rules)
        """
        impact_conds = impact_conditions or {}
        eligible: List[DecisionRule] = []

        for rule in self.list_rules(enabled_only=True):
            # Quality state check
            if quality_state.upper() not in [q.upper() for q in rule.required_data_quality]:
                continue

            # If quality is degraded (e.g. INSUFFICIENT_EVIDENCE / MISSING / CONFLICT),
            # only fallback rules should trigger.
            if quality_state.upper() in ["MISSING", "STALE", "INVALID", "CONFLICT", "INSUFFICIENT_EVIDENCE"]:
                if "MISSING" in rule.required_data_quality or "INSUFFICIENT_EVIDENCE" in rule.required_data_quality:
                    eligible.append(rule)
                continue

            # Risk tier check for risk-bound rules
            req_risk = rule.input_conditions.get("risk_tier")
            if req_risk is not None:
                if risk_tier is None:
                    continue
                if isinstance(req_risk, list):
                    if risk_tier.upper() not in [r.upper() for r in req_risk]:
                        continue
                elif risk_tier.upper() != str(req_risk).upper():
                    continue

            # Hazard type check
            h_type_match = "ALL" in rule.hazard_types or hazard_type.upper() in [h.upper() for h in rule.hazard_types]
            if not h_type_match:
                continue

            # Hazard state check
            h_state_match = "ALL" in rule.required_hazard_states or hazard_state.upper() in [
                s.upper() for s in rule.required_hazard_states
            ]
            if not h_state_match:
                continue

            # Official source requirement check
            if rule.official_source_requirement == "OFFICIAL_EVACUATION" and not has_official_evacuation:
                continue
            if rule.official_source_requirement == "OFFICIAL" and not has_official_source:
                continue

            # Impact conditions check
            impact_match = True
            for k, req_v in rule.required_impact_conditions.items():
                actual_v = impact_conds.get(k)
                if actual_v != req_v:
                    impact_match = False
                    break
            if not impact_match:
                continue

            eligible.append(rule)

        # Sort eligible rules by priority: IMMEDIATE_ATTENTION first, then HIGH, ROUTINE, INFORMATIONAL
        priority_order = {
            PriorityClass.IMMEDIATE_ATTENTION: 0,
            PriorityClass.HIGH: 1,
            PriorityClass.ROUTINE: 2,
            PriorityClass.INFORMATIONAL: 3,
        }
        eligible.sort(key=lambda r: priority_order.get(r.priority, 99))
        return eligible


# Canonical singleton
decision_rule_registry = DecisionRuleRegistry()

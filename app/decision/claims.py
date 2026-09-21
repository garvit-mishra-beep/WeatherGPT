"""Decision claims and Claim Gate validator for VAYUBODHAK Phase 8 — Decision Support & Nirnay Engine.

Registers approved decision claims in the Phase 2A ClaimRegistry and implements
DecisionClaimValidator to deterministically prevent alarmist, ungrounded, or statutory
impersonation statements in emitted action recommendations.
"""

from typing import List, Optional, Tuple
from app.decision.models import ActionRecommendation
from app.evidence.claim_gate import ClaimRegistry, claim_registry
from app.evidence.models import ClaimLifecycleStatus, ClaimRecord


# Explicit prohibited patterns across all decision outputs
UNIVERSAL_PROHIBITED_WORDS = [
    "people will die",
    "fatalities expected",
    "fatalities will occur",
    "death toll",
    "casualties forecast",
    "guaranteed crop failure",
    "guaranteed compensation",
    "insurance payout guaranteed",
    "loss will definitely occur",
]

UNSUPPORTED_EVACUATION_WORDS = [
    "evacuate immediately",
    "everyone must evacuate",
    "government has ordered evacuation",
    "mandatory evacuation order",
    "evacuation order issued by vayubodhak",
    "order all residents to leave",
]

UNSUPPORTED_ROAD_CLOSURE_WORDS = [
    "road officially closed",
    "road closed by authorities",
    "highway officially shut down",
    "traffic prohibited by police",
]

FALSE_SAFETY_WORDS = [
    "you are safe",
    "all clear guaranteed",
    "safe from danger",
    "no threat exists",
    "zero risk guaranteed",
]


def register_decision_claims(registry: ClaimRegistry = claim_registry) -> None:
    """Registers Phase 8 decision-specific claims into the Phase 2A Claim Registry."""

    claims: List[ClaimRecord] = [
        # 1. Official Warning Bulletin Pass-Through
        ClaimRecord(
            claim_id="CLAIM-DEC-OFFICIAL-001",
            claim_text="Pass through verified official meteorological warnings from IMD/NDMA verbatim preserving legal authority.",
            evidence_references=["SRC-IMD-BULLETINS", "SRC-NDMA-SACHET"],
            applicability="Active official alerts with verified spatial relevance",
            what_it_proves="Proves the presence, exact text, and validity bounds of an official government warning.",
            what_it_does_not_prove="Does NOT prove autonomous VAYUBODHAK command authority.",
            supported_component="DECISION",
            permitted_wording=[
                "Official {authority} warning bulletin: {headline}",
                "Active {warning_level} warning issued by {authority}",
                "Follow official instructions issued by local disaster management authorities",
            ],
            prohibited_wording=UNIVERSAL_PROHIBITED_WORDS,
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="VAYUBODHAK Nirnay Engine Phase 8",
            geography="India",
            time_basis="Contemporaneous Assessment",
            source_version="v1.0",
        ),

        # 2. Official Evacuation Directive Pass-Through
        ClaimRecord(
            claim_id="CLAIM-DEC-EVAC-001",
            claim_text="Pass through statutory government evacuation orders issued by NDMA or District Magistrate.",
            evidence_references=["SRC-NDMA-DIRECTIVE", "SRC-DDMA-ORDERS"],
            applicability="Statutory evacuation decrees issued by constitutional emergency authorities",
            what_it_proves="Proves existence and text of official government evacuation directives.",
            what_it_does_not_prove="Does NOT empower VAYUBODHAK to invent or mandate independent evacuation orders.",
            supported_component="DECISION",
            permitted_wording=[
                "Official evacuation order issued by {authority}",
                "Statutory evacuation decree in effect for {geography} until {valid_to}",
            ],
            prohibited_wording=UNIVERSAL_PROHIBITED_WORDS,
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="VAYUBODHAK Nirnay Engine Phase 8",
            geography="India",
            time_basis="Contemporaneous Assessment",
            source_version="v1.0",
        ),

        # 3. Road Inundation Caution & Local Verification
        ClaimRecord(
            claim_id="CLAIM-DEC-ROAD-001",
            claim_text="Recommend travel caution and local road clearance verification based on prototype corridor disruption.",
            evidence_references=["SRC-IRC-STANDARDS", "SRC-VAYUBODHAK-PROTOTYPE"],
            applicability="Road segments exposed to waterlogging or heavy rainfall triggers",
            what_it_proves="Proves presence of potential trafficability impediment requiring field verification.",
            what_it_does_not_prove="Does NOT prove legal road closure or police traffic prohibition.",
            supported_component="DECISION",
            permitted_wording=[
                "Potential road corridor waterlogging detected; verify local route passability",
                "Exercise caution on exposed transportation corridors; check local traffic police updates",
                "Scenario-based road disruption estimated; operational verification required",
            ],
            prohibited_wording=UNIVERSAL_PROHIBITED_WORDS + UNSUPPORTED_ROAD_CLOSURE_WORDS,
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="VAYUBODHAK Nirnay Engine Phase 8",
            geography="India",
            time_basis="Contemporaneous Assessment",
            source_version="v1.0",
        ),

        # 4. Healthcare Lifeline Continuity
        ClaimRecord(
            claim_id="CLAIM-DEC-HOSP-001",
            claim_text="Support facility management in coordinating auxiliary power, feeder road access, and bed surge review.",
            evidence_references=["SRC-WHO-HSI", "SRC-NDMA-HOSPITAL"],
            applicability="Healthcare facilities in hazard-affected zones",
            what_it_proves="Proves operational capacity at risk under external lifeline disruption.",
            what_it_does_not_prove="Does NOT prove patient mortality, hospital closure, or ICU evacuation mandate.",
            supported_component="DECISION",
            permitted_wording=[
                "Coordinate auxiliary power backups and verify emergency feeder road accessibility",
                "Review inpatient capacity strain and ensure essential medical supply reserves",
            ],
            prohibited_wording=UNIVERSAL_PROHIBITED_WORDS + ["hospital closed", "evacuate patients"],
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="VAYUBODHAK Nirnay Engine Phase 8",
            geography="India",
            time_basis="Contemporaneous Assessment",
            source_version="v1.0",
        ),

        # 5. Educational Shelter Suitability
        ClaimRecord(
            claim_id="CLAIM-DEC-SCHL-001",
            claim_text="Flag educational facilities for administrative dual-use emergency shelter suitability inspection.",
            evidence_references=["SRC-NDMA-SCHOOL", "SRC-VAYUBODHAK-PROTOTYPE"],
            applicability="Schools in hazard zones evaluated for shelter potential",
            what_it_proves="Proves preliminary physical suitability assessment for municipal shelter planning.",
            what_it_does_not_prove="Does NOT certify official shelter designation without local district inspection.",
            supported_component="DECISION",
            permitted_wording=[
                "Verify facility dual-use emergency shelter suitability with local administration",
                "Preliminary shelter suitability assessment flagged for district review",
            ],
            prohibited_wording=UNIVERSAL_PROHIBITED_WORDS,
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="VAYUBODHAK Nirnay Engine Phase 8",
            geography="India",
            time_basis="Contemporaneous Assessment",
            source_version="v1.0",
        ),

        # 6. Agricultural Flowering Preparedness
        ClaimRecord(
            claim_id="CLAIM-DEC-AGRI-001",
            claim_text="Advise agronomic protective measures for crops during sensitive anthesis/flowering stages.",
            evidence_references=["SRC-ICAR-AGROMET", "SRC-FAO-CROP"],
            applicability="Standing crops during flowering/anthesis subject to extreme temperature or moisture stress",
            what_it_proves="Proves research-grounded protective measures to mitigate phenological yield loss.",
            what_it_does_not_prove="Does NOT prove guaranteed crop failure or insurance compensation entitlements.",
            supported_component="DECISION",
            permitted_wording=[
                "Maintain light frequent irrigation to moderate microclimate during critical flowering stage",
                "Ensure drainage channels are clear to prevent standing water submergence",
            ],
            prohibited_wording=UNIVERSAL_PROHIBITED_WORDS,
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="VAYUBODHAK Nirnay Engine Phase 8",
            geography="India",
            time_basis="Contemporaneous Assessment",
            source_version="v1.0",
        ),

        # 7. Multi-Sector Cyclone Preparedness
        ClaimRecord(
            claim_id="CLAIM-DEC-CYCLONE-001",
            claim_text="Advise multi-sector preparedness actions under severe cyclonic weather warnings.",
            evidence_references=["SRC-NDMA-CYCLONE", "SRC-IMD-SOP"],
            applicability="Coastal and inland zones under cyclonic storm warnings",
            what_it_proves="Proves standard civil preparedness protocols recommended during cyclonic alerts.",
            what_it_does_not_prove="Does NOT supersede district magistrate or state disaster management decrees.",
            supported_component="DECISION",
            permitted_wording=[
                "Secure loose outdoor structures, trim vulnerable tree limbs, and store emergency essentials",
                "Fishermen advised strictly to avoid venturing into deep sea waters",
            ],
            prohibited_wording=UNIVERSAL_PROHIBITED_WORDS,
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="VAYUBODHAK Nirnay Engine Phase 8",
            geography="India",
            time_basis="Contemporaneous Assessment",
            source_version="v1.0",
        ),

        # 8. Extreme Heat Protection
        ClaimRecord(
            claim_id="CLAIM-DEC-HEAT-001",
            claim_text="Advise public health hydration and outdoor exposure reduction during severe heatwaves.",
            evidence_references=["SRC-NDMA-HEAT-ACTION-PLAN", "SRC-IMD-HEAT"],
            applicability="Regions subject to IMD heatwave or severe heatwave warnings",
            what_it_proves="Proves evidence-supported personal heat illness mitigation measures.",
            what_it_does_not_prove="Does NOT constitute individual clinical or medical prescriptions.",
            supported_component="DECISION",
            permitted_wording=[
                "Avoid strenuous outdoor activity between 12:00 and 15:00 IST; maintain continuous hydration",
                "Provide shade and adequate drinking water for outdoor livestock and vulnerable persons",
            ],
            prohibited_wording=UNIVERSAL_PROHIBITED_WORDS,
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="VAYUBODHAK Nirnay Engine Phase 8",
            geography="India",
            time_basis="Contemporaneous Assessment",
            source_version="v1.0",
        ),

        # 9. Insufficient Evidence Safety Fallback
        ClaimRecord(
            claim_id="CLAIM-DEC-INSUFFICIENT-001",
            claim_text="Maintain monitoring and avoid asserting safety when evidence is missing or stale.",
            evidence_references=["SRC-VAYUBODHAK-GOVERNANCE"],
            applicability="Assessments with missing, stale, or conflicting observations",
            what_it_proves="Proves adherence to precautionary safety boundaries under observational uncertainty.",
            what_it_does_not_prove="Does NOT prove the absence of physical hazard.",
            supported_component="DECISION",
            permitted_wording=[
                "Observational evidence is insufficient to evaluate operational safety; maintain active monitoring",
                "Data coverage is incomplete; seek official bulletins before undertaking critical operations",
            ],
            prohibited_wording=FALSE_SAFETY_WORDS,
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="VAYUBODHAK Nirnay Engine Phase 8",
            geography="India",
            time_basis="Contemporaneous Assessment",
            source_version="v1.0",
        ),
    ]

    for c in claims:
        registry.register_claim(c)


class DecisionClaimValidator:
    """Validates emitted decision text and recommendations against strict safety boundaries."""

    def __init__(self, registry: ClaimRegistry = claim_registry) -> None:
        self.registry = registry
        register_decision_claims(self.registry)

    def validate_action_text(
        self,
        text: str,
        has_official_evacuation: bool = False,
        has_official_closure: bool = False,
        quality_state: str = "VALID",
    ) -> Tuple[bool, Optional[str]]:
        """Checks text for prohibited alarmist, casualty, false safety, or unauthorized directive claims.
        
        Returns:
            Tuple of (is_valid: bool, violation_reason: Optional[str])
        """
        text_lower = text.lower()

        # 1. Universal Prohibitions (Casualties, Fatalities, Guaranteed Loss)
        for pattern in UNIVERSAL_PROHIBITED_WORDS:
            if pattern in text_lower:
                return False, f"Prohibited casualty or certainty claim: '{pattern}'"

        # 2. Unsupported Evacuation Directives
        if not has_official_evacuation:
            for pattern in UNSUPPORTED_EVACUATION_WORDS:
                if pattern in text_lower:
                    return False, f"Unauthorized evacuation directive without official government order: '{pattern}'"

        # 3. Unsupported Road Closures
        if not has_official_closure:
            for pattern in UNSUPPORTED_ROAD_CLOSURE_WORDS:
                if pattern in text_lower:
                    return False, f"Unauthorized official road closure claim without statutory evidence: '{pattern}'"

        # 4. False Safety Guarantees under Missing/Degraded Evidence
        if quality_state.upper() in ["MISSING", "STALE", "INVALID", "CONFLICT", "INSUFFICIENT_EVIDENCE"]:
            for pattern in FALSE_SAFETY_WORDS:
                if pattern in text_lower:
                    return False, f"False safety guarantee prohibited when evidence is {quality_state}: '{pattern}'"

        return True, None

    def validate_action_recommendation(
        self,
        action: ActionRecommendation,
        has_official_evacuation: bool = False,
        has_official_closure: bool = False,
        quality_state: str = "VALID",
    ) -> None:
        """Validates an ActionRecommendation, raising ValueError if safety boundaries are violated."""
        combined_text = f"{action.headline} {action.description}"
        is_valid, reason = self.validate_action_text(
            text=combined_text,
            has_official_evacuation=has_official_evacuation,
            has_official_closure=has_official_closure,
            quality_state=quality_state,
        )
        if not is_valid:
            raise ValueError(f"Decision Claim Gate rejected action '{action.action_id}': {reason}")


# Canonical singleton
decision_claim_validator = DecisionClaimValidator()

"""Deterministic Claim Registry and Claim Gate for VAYUBODHAK Phase 2A.

Enforces strict provenance guardrails:
- Rejects DRAFT claims from runtime emission
- Rejects RETIRED claims
- Allows APPROVED claims with supporting evidence
- Enforces permitted wording and rejects prohibited wording
- Preserves audit traceability

CRITICAL PRINCIPLE:
The Claim Gate is a provenance guardrail ensuring that claims match their
registered governance rules. It is NOT proof that the underlying source is
scientifically infallible.
"""

from datetime import datetime, timezone
import re
from typing import Dict, List, Optional
from app.evidence.models import (
    ClaimGateEvaluation,
    ClaimGateResultStatus,
    ClaimLifecycleStatus,
    ClaimRecord,
)


class ClaimRegistry:
    """Catalog of approved, draft, and retired operational and factual claims."""

    def __init__(self) -> None:
        self._claims: Dict[str, ClaimRecord] = {}
        self._initialize_canonical_claims()

    def _initialize_canonical_claims(self) -> None:
        """Seeds canonical claims based on VAYUBODHAK research."""
        canonical_claims: List[ClaimRecord] = [
            # 1. IMD Red Alert Warning Claim
            ClaimRecord(
                claim_id="CLM-IMD-RED-ALERT",
                claim_text="IMD has issued a Red Alert (Take Action) for extremely heavy rainfall (>204.4 mm in 24 hours).",
                evidence_references=["EVD-IMD-REF-01"],
                applicability="Active official IMD CAP warning bulletin with warning_level=Red and hazard='Heavy Rainfall'",
                what_it_proves="Proves that the statutory national authority (IMD) has issued its highest-level operational weather warning for the specified administrative boundary.",
                what_it_does_not_prove="Does NOT prove building-level structural inundation or street-by-street waterlogging depths.",
                supported_component="ALERTS",
                permitted_wording=[
                    "IMD Red Alert in effect",
                    "Extremely heavy rainfall warning issued by IMD",
                    "Authorities advise taking immediate action"
                ],
                prohibited_wording=[
                    "VAYUBODHAK declared a red alert",
                    "Mandatory evacuation ordered by WeatherGPT",
                    "100% guaranteed catastrophic flooding across all sectors"
                ],
                lifecycle_status=ClaimLifecycleStatus.APPROVED,
                exact_locator="IMD CAP Bulletin / Warning Code RED",
                geography="India",
                time_basis="24h Operational Warning Window",
                source_version="IMD_CAP_v1.0",
            ),
            # 2. IMD Orange Alert Warning Claim
            ClaimRecord(
                claim_id="CLM-IMD-ORANGE-ALERT",
                claim_text="IMD has issued an Orange Alert (Be Prepared) for very heavy rainfall (115.6 - 204.4 mm in 24 hours).",
                evidence_references=["EVD-IMD-REF-02"],
                applicability="Active official IMD CAP warning bulletin with warning_level=Orange",
                what_it_proves="Proves that IMD forecasts severe weather requiring heightened readiness by disaster authorities and the public.",
                what_it_does_not_prove="Does NOT prove direct infrastructure failure or localized river embankment breach.",
                supported_component="ALERTS",
                permitted_wording=[
                    "IMD Orange Alert (Be Prepared)",
                    "Very heavy rainfall expected per IMD advisory",
                    "Monitor official bulletins and prepare contingency measures"
                ],
                prohibited_wording=[
                    "No preparation needed",
                    "Emergency lockdown enforced by VAYUBODHAK",
                    "Definite flood disaster"
                ],
                lifecycle_status=ClaimLifecycleStatus.APPROVED,
                exact_locator="IMD CAP Bulletin / Warning Code ORANGE",
                geography="India",
                time_basis="24h Operational Warning Window",
                source_version="IMD_CAP_v1.0",
            ),
            # 3. FAO-56 Crop Water Deficit Claim
            ClaimRecord(
                claim_id="CLM-AGRI-WATER-DEFICIT",
                claim_text="Daily crop evapotranspiration (ETc) exceeds effective rainfall and root-zone soil moisture reserves, indicating soil moisture depletion.",
                evidence_references=["EVD-AGRI-REF-01"],
                applicability="Calculated FAO-56 dual crop coefficient water balance with soil moisture < readily available water (RAW)",
                what_it_proves="Proves that crops are under moisture stress requiring supplemental irrigation based on FAO-56 physiological formulas.",
                what_it_does_not_prove="Does NOT prove canal water availability, pump electricity supply, or deep aquifer depletion.",
                supported_component="AGRICULTURE",
                permitted_wording=[
                    "Irrigation is recommended due to soil moisture deficit",
                    "Crop water balance indicates critical irrigation window",
                    "Root-zone moisture is depleting below optimal threshold"
                ],
                prohibited_wording=[
                    "Crop will 100% die today",
                    "Guaranteed complete yield failure",
                    "Government declared drought"
                ],
                lifecycle_status=ClaimLifecycleStatus.APPROVED,
                exact_locator="FAO Irrigation and Drainage Paper 56 Eq 84",
                geography="India Agricultural Zones",
                time_basis="Daily Agronomic Step",
                source_version="FAO56-v1.0",
            ),
            # 4. Draft Prototype Claim (for testing gate rejection)
            ClaimRecord(
                claim_id="CLM-PROTOTYPE-MICROCLIMATE-01",
                claim_text="Experimental microclimate sensor network indicates 3.2 deg C urban heat island disparity.",
                evidence_references=[],
                applicability="Uncalibrated IoT mesh prototype",
                what_it_proves="Experimental prototype sensor disparity only.",
                what_it_does_not_prove="Does NOT prove official meteorological temperature or heatwave criterion.",
                supported_component="RESEARCH",
                permitted_wording=["Prototype observation indicates local variation"],
                prohibited_wording=["Official heatwave declared"],
                lifecycle_status=ClaimLifecycleStatus.DRAFT,
                exact_locator="Mesh Node #4",
                geography="Urban Testbed",
                time_basis="Hourly",
                source_version="Prototype-0.1",
            ),
            # 5. Retired Historical Claim (for testing gate rejection)
            ClaimRecord(
                claim_id="CLM-HIST-LEGACY-NORMALS-1980",
                claim_text="Rainfall normal calculated against 1951-1980 baseline.",
                evidence_references=["EVD-HIST-01"],
                applicability="Superseded climatological normal period",
                what_it_proves="Historical 30-year normal for past operational epoch.",
                what_it_does_not_prove="Does NOT prove current climatological normal (superseded by WMO 1991-2020 standard).",
                supported_component="CLIMATE",
                permitted_wording=["Historical 1951-1980 epoch baseline"],
                prohibited_wording=["Current official normal", "Present-day climate baseline"],
                lifecycle_status=ClaimLifecycleStatus.RETIRED,
                exact_locator="IMD Climatological Normals 1951-1980",
                geography="India",
                time_basis="30-year epoch",
                source_version="IMD_1980_RETIRED",
            ),
        ]

        for c in canonical_claims:
            self._claims[c.claim_id] = c

    def register_claim(self, claim: ClaimRecord) -> ClaimRecord:
        """Registers or updates a claim record."""
        self._claims[claim.claim_id] = claim
        return claim

    def get_claim(self, claim_id: str) -> Optional[ClaimRecord]:
        """Retrieves a claim by ID."""
        return self._claims.get(claim_id)

    def list_claims(self, status: Optional[ClaimLifecycleStatus] = None) -> List[ClaimRecord]:
        """Lists claims, optionally filtered by lifecycle status."""
        if status:
            return [c for c in self._claims.values() if c.lifecycle_status == status]
        return list(self._claims.values())


class ClaimGate:
    """Deterministic validation gate evaluating claims for operational runtime safety."""

    def __init__(self, registry: Optional[ClaimRegistry] = None) -> None:
        self.registry = registry or ClaimRegistry()

    def evaluate_claim(
        self,
        claim_id: str,
        proposed_text: Optional[str] = None,
        attached_evidence_ids: Optional[List[str]] = None,
    ) -> ClaimGateEvaluation:
        """Evaluates a claim record against deterministic provenance rules.
        
        Rules:
        1. Claim must exist in the Claim Registry.
        2. DRAFT claims MUST be rejected for runtime release.
        3. RETIRED claims MUST be rejected for runtime release.
        4. APPROVED claims require at least one supporting evidence reference.
        5. If proposed_text is provided, it must not match any prohibited_wording pattern.
        """
        now = datetime.now(timezone.utc)
        claim = self.registry.get_claim(claim_id)

        if not claim:
            return ClaimGateEvaluation(
                claim_id=claim_id,
                status=ClaimGateResultStatus.REJECT,
                lifecycle_status=ClaimLifecycleStatus.DRAFT,
                is_runtime_eligible=False,
                reasons=[f"Claim '{claim_id}' not found in Claim Registry."],
                permitted_wording=[],
                prohibited_wording=[],
                violations_detected=["UNREGISTERED_CLAIM"],
                evaluated_at=now,
            )

        reasons: List[str] = []
        violations: List[str] = []

        # 1. Lifecycle Check
        if claim.lifecycle_status == ClaimLifecycleStatus.DRAFT:
            reasons.append("Claim is in DRAFT status; not approved for operational runtime release.")
            violations.append("DRAFT_CLAIM_REJECTED")

        elif claim.lifecycle_status == ClaimLifecycleStatus.RETIRED:
            reasons.append("Claim is RETIRED; superseded and invalid for active runtime release.")
            violations.append("RETIRED_CLAIM_REJECTED")

        # 2. Evidence Reference Check
        combined_evidence = set(claim.evidence_references)
        if attached_evidence_ids:
            combined_evidence.update(attached_evidence_ids)

        if not combined_evidence and claim.lifecycle_status == ClaimLifecycleStatus.APPROVED:
            reasons.append("Approved claim lacks supporting evidence references.")
            violations.append("MISSING_EVIDENCE_REFERENCES")

        # 3. Wording Violation Check (if proposed statement text provided)
        if proposed_text and claim.prohibited_wording:
            lower_text = proposed_text.lower()
            for prohibited in claim.prohibited_wording:
                # Substring check for forbidden overclaiming
                if prohibited.lower() in lower_text:
                    violations.append(f"PROHIBITED_WORDING: '{prohibited}'")
                    reasons.append(f"Proposed text contains prohibited wording: '{prohibited}'.")

        # Decision
        is_allowed = (len(violations) == 0) and (claim.lifecycle_status == ClaimLifecycleStatus.APPROVED)
        status = ClaimGateResultStatus.ALLOW if is_allowed else ClaimGateResultStatus.REJECT

        if is_allowed:
            reasons.append("Claim verified: APPROVED lifecycle status, valid evidence references, zero wording violations.")

        return ClaimGateEvaluation(
            claim_id=claim_id,
            status=status,
            lifecycle_status=claim.lifecycle_status,
            is_runtime_eligible=is_allowed,
            reasons=reasons,
            permitted_wording=claim.permitted_wording,
            prohibited_wording=claim.prohibited_wording,
            violations_detected=violations,
            evaluated_at=now,
        )


# Singleton instances
claim_registry = ClaimRegistry()
claim_gate = ClaimGate(claim_registry)

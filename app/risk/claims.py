"""Risk claims for the Phase 2A Claim Registry.

Registers approved claims that the risk engine may reference when producing
quantitative risk evaluations. Enforces strict negative boundaries preventing
risk scores from being represented as damage, financial loss, casualties,
fatalities, evacuation orders, or statutory warnings.
"""

from typing import List
from app.evidence.claim_gate import ClaimRegistry, claim_registry
from app.evidence.models import ClaimLifecycleStatus, ClaimRecord


def register_risk_claims(registry: ClaimRegistry = claim_registry) -> None:
    """Registers risk-specific claims into the Phase 2A Claim Registry."""

    claims: List[ClaimRecord] = [
        # 1. Multiplicative Risk Quantification Claim
        ClaimRecord(
            claim_id="CLM-RISK-ASSESSMENT-001",
            claim_text=(
                "Deterministic prototype quantitative risk assessment combining verified "
                "hazard, exposure, and vulnerability evidence via multiplicative interaction, "
                "within broader disaster-risk conceptual frameworks."
            ),
            evidence_references=["SRC-UNDRR-TERMINOLOGY-2017", "SRC-SENDAI-FRAMEWORK", "SRC-VAYUBODHAK-PROTOTYPE"],
            applicability="Exposed asset or population entity with verified hazard, exposure, and vulnerability inputs",
            what_it_proves=(
                "Proves the relative, dimensionless compounding interaction of normalized hazard intensity, "
                "spatial asset presence, and systemic susceptibility under VAYUBODHAK prototype scoring."
            ),
            what_it_does_not_prove=(
                "Does NOT prove structural collapse, physical damage percentages, repair costs, "
                "injuries, casualties, fatalities, evacuation mandates, or official weather warnings. "
                "Does NOT represent an official UNDRR or IPCC prescribed mathematical equation or certified loss probability. "
                "Does NOT model coping/adaptive capacity."
            ),
            supported_component="RISK",
            permitted_wording=[
                "VAYUBODHAK prototype quantitative risk index is evaluated as {category} ({score})",
                "Quantitative risk index is evaluated as {category} ({score})",
                "Multiplicative interaction score of hazard, exposure, and susceptibility is {score}",
                "Relative compound precarity index is categorized as {category}",
                "Deterministic risk evaluation indicates {category} prioritization",
            ],
            prohibited_wording=[
                "guaranteed casualties",
                "fatalities",
                "death toll",
                "damage amount",
                "monetary loss",
                "economic loss in rupees",
                "mandatory evacuation",
                "evacuation order",
                "road closed",
                "hospital closed",
                "official warning",
                "statutory alert",
                "UNDRR defines R = H x E x V",
                "UNDRR defines R = H × E × V",
                "IPCC defines R = H x E x V",
                "IPCC defines R = H × E × V",
                "UNDRR mandates multiplicative risk",
                "IPCC mandates multiplicative risk",
                "UNDRR risk score",
                "IPCC risk score",
                "IPCC validated thresholds",
                "UNDRR formula",
                "IPCC formula",
                "complete UNDRR risk implementation",
            ],
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="UNDRR Disaster Risk Framework / VAYUBODHAK RISK-METH-MULT-001 Prototype",
            geography="India",
            time_basis="Contemporaneous Forecast / Historical Census Baseline",
            source_version="v1.0",
        ),

        # 2. Methodological Limitation & Prototype Disclosure Claim
        ClaimRecord(
            claim_id="CLM-RISK-LIMITATION-001",
            claim_text="Disclose prototype status, input uncertainties, and non-predictive nature of risk scores.",
            evidence_references=["SRC-VAYUBODHAK-GOVERNANCE"],
            applicability="All VAYUBODHAK risk evaluations and derivative summaries",
            what_it_proves="Proves compliance with scientific honesty and uncertainty disclosure requirements.",
            what_it_does_not_prove="Does NOT reduce or manipulate the calculated risk score magnitude.",
            supported_component="RISK",
            permitted_wording=[
                "VAYUBODHAK prototype risk assessment reflects relative precarity and does not constitute damage or casualty forecasts",
                "Risk scores are dimensionless indices and do not predict monetary losses or structural collapse",
                "Passing automated software tests verifies implementation correctness only; it does not independently validate empirical real-world risk fidelity",
            ],
            prohibited_wording=[
                "scientifically certified casualty probability",
                "empirical fatality certainty",
                "statutory disaster declaration",
            ],
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="VAYUBODHAK Governance Specification v1.0",
            geography="Global",
            time_basis="Always Applicable",
            source_version="v1.0",
        ),

        # 3. Legacy Additive Operational Index Claim
        ClaimRecord(
            claim_id="CLM-RISK-ADDITIVE-001",
            claim_text="Operational multi-criteria weighted risk index for monitoring prioritization.",
            evidence_references=["SRC-WMO-1150", "SRC-VAYUBODHAK-ANALYTICS-DOC11"],
            applicability="Operational dashboards utilizing legacy additive weighted combinations (0.50H + 0.30E + 0.20V)",
            what_it_proves="Proves operational screening priority on a 0-10 scale for monitoring.",
            what_it_does_not_prove="Does NOT satisfy physical zero-boundary disaster risk conditions.",
            supported_component="RISK",
            permitted_wording=[
                "Operational multi-criteria monitoring priority index is {score}/10",
                "Legacy operational composite index is evaluated as {category}",
            ],
            prohibited_wording=[
                "exact physical disaster risk",
                "zero-boundary compliant risk",
                "fatalities",
                "damage cost",
            ],
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="VAYUBODHAK Analytics Engine Spec docs/11_ANALYTICS_ENGINE.md §4.2",
            geography="India",
            time_basis="Operational Forecast Window",
            source_version="v1.0",
        ),
    ]

    for claim in claims:
        registry.register_claim(claim)


# Register claims on module import
register_risk_claims()

"""Impact claims for the Phase 2A Claim Registry.

Registers approved claims that the Potential Impact Engine may reference when producing
potential consequence assessments. Enforces strict Claim Gate boundaries preventing
impact estimates from asserting casualty predictions, fatalities, certain collapse,
statutory warnings, or evacuation mandates.
"""

from typing import List
from app.evidence.claim_gate import ClaimRegistry, claim_registry
from app.evidence.models import ClaimLifecycleStatus, ClaimRecord


def register_impact_claims(registry: ClaimRegistry = claim_registry) -> None:
    """Registers impact-specific claims into the Phase 2A Claim Registry."""

    claims: List[ClaimRecord] = [
        # 1. Deterministic Potential Impact Modeling Claim
        ClaimRecord(
            claim_id="CLM-IMPACT-MODEL-001",
            claim_text=(
                "Deterministic prototype potential impact modeling estimating physical damage states, "
                "infrastructure disruption, service capacity strain, agricultural yield consequences, "
                "and direct asset replacement costs from verified hazard, exposure, and vulnerability evidence."
            ),
            evidence_references=[
                "SRC-BMTPC-ATLAS",
                "SRC-IRC-ROAD-STANDARDS",
                "SRC-WHO-HSI",
                "SRC-ICAR-ADVISORIES",
                "SRC-CPWD-DSR",
                "SRC-VAYUBODHAK-PROTOTYPE",
            ],
            applicability="Exposed entities with verified hazard, exposure, and vulnerability assessments",
            what_it_proves=(
                "Proves estimated potential physical damage state, infrastructure disruption length, "
                "service capacity strain, agricultural yield loss percentage, or direct asset repair cost "
                "under explicit VAYUBODHAK prototype models."
            ),
            what_it_does_not_prove=(
                "Does NOT prove certain structural collapse, guaranteed financial loss, casualty counts, "
                "fatalities, hospital closures, official road closures, evacuation orders, or official warnings. "
                "Does NOT represent an empirically calibrated econometric or epidemiological model."
            ),
            supported_component="IMPACT",
            permitted_wording=[
                "Potential physical damage state is evaluated as {damage_state}",
                "Estimated damage ratio is {damage_ratio}",
                "Potential road infrastructure disruption length is {length} km",
                "Healthcare facility operational capacity at risk is {capacity} beds",
                "Educational facility potential operational disruption is evaluated",
                "Potential crop yield consequence is estimated as {pct}% across {acres} acres",
                "Estimated direct physical asset replacement cost is evaluated as {loss}",
                "Deterministic potential impact assessment indicates {damage_state} condition",
            ],
            prohibited_wording=[
                "buildings will definitely collapse",
                "will certainly collapse",
                "loss will occur",
                "guaranteed financial loss",
                "people will die",
                "fatalities",
                "casualties",
                "death toll",
                "hospital will certainly shut down",
                "hospital closed",
                "road closed by authorities",
                "evacuate immediately",
                "mandatory evacuation order",
                "relief priority 1",
                "official disaster warning",
                "empirically validated damage curve",
                "calibrated fatality prediction",
            ],
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="VAYUBODHAK Potential Impact Engine Phase 7",
            geography="India",
            time_basis="Contemporaneous Assessment",
            source_version="v1.0",
        ),

        # 2. Impact Uncertainty & Prototype Limitation Claim
        ClaimRecord(
            claim_id="CLM-IMPACT-LIMITATION-001",
            claim_text="Disclose prototype status, input uncertainties, and non-predictive nature of impact models.",
            evidence_references=["SRC-VAYUBODHAK-GOVERNANCE"],
            applicability="All VAYUBODHAK impact assessments and derivative reports",
            what_it_proves="Proves compliance with scientific governance and explicit uncertainty disclosure.",
            what_it_does_not_prove="Does NOT replace or alter computed consequence metrics.",
            supported_component="IMPACT",
            permitted_wording=[
                "VAYUBODHAK prototype impact models provide scenario-based consequence estimations and do not constitute casualty or certain collapse forecasts",
                "Impact estimates are deterministic engineering approximations and do not predict macroeconomic losses or guaranteed failure",
                "Passing automated software tests verifies implementation correctness only; it does not independently validate empirical real-world loss fidelity",
            ],
            prohibited_wording=[
                "statutory damage certification",
                "guaranteed fatality forecast",
                "official casualty figure",
            ],
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="VAYUBODHAK Governance Specification v1.0",
            geography="Global",
            time_basis="Standing Policy",
            source_version="v1.0",
        ),
    ]

    for claim in claims:
        registry.register_claim(claim)


# Execute registration on module import
register_impact_claims()

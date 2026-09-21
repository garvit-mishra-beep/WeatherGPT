"""Hazard-specific claims for the Phase 2A Claim Registry.

Registers approved claims that the hazard engine may reference when
producing deterministic hazard evaluations. Every documented
research-backed hazard claim must pass the Phase 2A Claim Gate.
"""

from app.evidence.models import ClaimLifecycleStatus, ClaimRecord
from app.evidence.claim_gate import ClaimRegistry


def register_hazard_claims(registry: ClaimRegistry) -> None:
    """Registers hazard-specific claims into the Phase 2A Claim Registry."""

    hazard_claims = [
        # 1. Heavy Rainfall — IMD Classification
        ClaimRecord(
            claim_id="CLM-HAZARD-HEAVY-RAIN-IMD",
            claim_text="24-hour rainfall accumulation meets or exceeds IMD heavy rainfall classification thresholds "
                       "(64.5mm heavy, 115.6mm very heavy, 204.5mm extremely heavy).",
            evidence_references=["EVD-RAIN-REF-01"],
            applicability="Active observed or forecast precipitation evidence with 24-hour accumulation for India",
            what_it_proves="Proves that the measured/forecast precipitation meets the IMD rainfall classification boundary.",
            what_it_does_not_prove="Does NOT prove flooding, waterlogging, infrastructure damage, or crop loss. "
                                  "A rainfall indicator does not automatically prove flooding.",
            supported_component="HAZARD",
            permitted_wording=[
                "Heavy rainfall recorded per IMD classification",
                "Very heavy rainfall forecast per IMD criteria",
                "Extremely heavy rainfall warning threshold met",
            ],
            prohibited_wording=[
                "VAYUBODHAK declares flood emergency",
                "Guaranteed infrastructure destruction",
                "Mandatory evacuation ordered by WeatherGPT",
            ],
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="IMD Standard Operational Guidelines 2024",
            geography="India",
            time_basis="24-hour accumulation period",
            source_version="IMD-2024-RAIN-v1.0",
        ),

        # 2. Heat — IMD Heatwave Criteria
        ClaimRecord(
            claim_id="CLM-HAZARD-HEAT-IMD",
            claim_text="Maximum temperature meets or exceeds IMD heatwave classification threshold for Plains (≥40°C).",
            evidence_references=["EVD-HEAT-REF-01"],
            applicability="Maximum daily temperature observation or forecast for India Plains region",
            what_it_proves="Proves that the temperature value meets the IMD heatwave classification threshold.",
            what_it_does_not_prove="Does NOT prove an official IMD heatwave declaration (requires official bulletin). "
                                  "Does NOT prove heat-related casualties or hospital admissions.",
            supported_component="HAZARD",
            permitted_wording=[
                "Temperature meets IMD heatwave threshold",
                "Heatwave conditions indicated by temperature data",
                "Elevated thermal stress conditions",
            ],
            prohibited_wording=[
                "Official heatwave declared by VAYUBODHAK",
                "Guaranteed heat-stroke fatalities",
                "Government mandatory cooling order",
            ],
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="IMD Heatwave Criteria (Plains)",
            geography="India Plains",
            time_basis="Daily maximum temperature",
            source_version="IMD-2024-HEAT-v1.0",
        ),

        # 3. Flood — CWC Official Warning
        ClaimRecord(
            claim_id="CLM-HAZARD-FLOOD-CWC",
            claim_text="CWC has issued an official hydrological flood warning for a specific gauging station or river basin.",
            evidence_references=["EVD-FLOOD-CWC-REF-01"],
            applicability="Active CWC official flood warning bulletin",
            what_it_proves="Proves that the statutory hydrological authority (CWC) has issued a flood warning "
                           "for the specified monitoring station or river basin.",
            what_it_does_not_prove="Does NOT prove nationwide flooding. "
                                  "CWC flood levels are station-specific and must NOT be silently interpolated nationwide. "
                                  "Does NOT prove structural building-level inundation depths.",
            supported_component="HAZARD",
            permitted_wording=[
                "CWC flood warning in effect for specified station",
                "Official hydrological alert issued by CWC",
                "River levels exceed warning threshold at gauging station",
            ],
            prohibited_wording=[
                "VAYUBODHAK declares nationwide flood",
                "Universal flood warning for all of India",
                "Guaranteed dam breach or embankment failure",
            ],
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="CWC Flood Forecast Bulletin",
            geography="CWC-monitored river basins",
            time_basis="Active hydrological warning period",
            source_version="CWC-2024-FLOOD-v1.0",
        ),

        # 4. Cyclone — IMD Classification
        ClaimRecord(
            claim_id="CLM-HAZARD-CYCLONE-IMD",
            claim_text="IMD has issued an official cyclone warning classifying the disturbance on the 8-stage intensity scale.",
            evidence_references=["EVD-CYCLONE-IMD-REF-01"],
            applicability="Active IMD cyclone warning bulletin",
            what_it_proves="Proves that IMD has classified and issued a warning for a tropical cyclonic disturbance.",
            what_it_does_not_prove="Does NOT prove exact landfall location, precise storm surge heights, "
                                  "or building-level wind damage without hydrodynamic models.",
            supported_component="HAZARD",
            permitted_wording=[
                "IMD cyclone warning in effect",
                "Cyclonic storm classified per IMD 8-stage scale",
                "Official cyclone advisory issued by IMD",
            ],
            prohibited_wording=[
                "VAYUBODHAK cyclone warning",
                "Guaranteed complete destruction of coastal infrastructure",
                "Mandatory national evacuation ordered",
            ],
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="IMD Cyclone Warning Bulletin",
            geography="Indian Ocean basin",
            time_basis="Active cyclone warning period",
            source_version="IMD-2024-CYCLONE-v1.0",
        ),
    ]

    for claim in hazard_claims:
        registry.register_claim(claim)

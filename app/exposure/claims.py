"""Exposure-specific claims for the Phase 2A Claim Registry.

Registers approved claims that the exposure engine may reference when
producing quantified exposure evaluations. Enforces boundaries between
exposure presence and damage/vulnerability inferences.
"""

from typing import List
from app.evidence.models import ClaimLifecycleStatus, ClaimRecord
from app.evidence.claim_gate import ClaimRegistry, claim_registry


def register_exposure_claims(registry: ClaimRegistry = claim_registry) -> None:
    """Registers exposure-specific claims into the Phase 2A Claim Registry."""

    claims: List[ClaimRecord] = [
        # 1. Population Exposure
        ClaimRecord(
            claim_id="CLM-EXPOSURE-POP-001",
            claim_text="Estimated population residing within the spatial boundary of an active hazard.",
            evidence_references=["SRC-CENSUS-INDIA-2011", "SRC-WORLDPOP-GRID"],
            applicability="Active hazard footprint with census or gridded population data",
            what_it_proves="Proves geographic overlap of residential demographic baseline with the hazard boundary.",
            what_it_does_not_prove="Does NOT prove mortality, injuries, evacuation necessity, structural damage, or casualties.",
            supported_component="EXPOSURE",
            permitted_wording=[
                "Estimated exposed population is {count} persons",
                "Approximately {count} residents located within hazard boundary",
                "Area-weighted population estimate indicates {count} individuals",
            ],
            prohibited_wording=[
                "casualties",
                "fatalities",
                "deaths",
                "injured",
                "hospitalized",
                "evacuated",
                "guaranteed headcount",
                "exact current population",
            ],
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="Census of India 2011 / WorldPop 2020",
            geography="India",
            time_basis="Census Baseline 2011 / Grid 2020",
            source_version="v1.0",
        ),

        # 2. Critical Point Infrastructure
        ClaimRecord(
            claim_id="CLM-EXPOSURE-ASSET-001",
            claim_text="Critical point infrastructure facilities located within the hazard perimeter.",
            evidence_references=["SRC-MOHFW-FACILITIES", "SRC-OSM-INDIA"],
            applicability="Active hazard boundary intersecting verified facility coordinates",
            what_it_proves="Proves physical presence of facility coordinates inside the hazard boundary.",
            what_it_does_not_prove="Does NOT prove structural damage, loss of function, or operational interruption.",
            supported_component="EXPOSURE",
            permitted_wording=[
                "{count} critical facilities situated within hazard perimeter",
                "Identified {count} hospitals/schools inside warning zone",
            ],
            prohibited_wording=[
                "facility damaged",
                "hospital destroyed",
                "inoperable",
                "power grid collapsed",
                "structural failure",
            ],
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="National Infrastructure Database",
            geography="India",
            time_basis="Static GIS Registry",
            source_version="v1.0",
        ),

        # 3. Linear Transport Infrastructure (Roads)
        ClaimRecord(
            claim_id="CLM-EXPOSURE-ROAD-001",
            claim_text="Linear road and highway centerline kilometers intersecting the hazard boundary.",
            evidence_references=["SRC-NHAI-HIGHWAYS"],
            applicability="Active hazard polygon intersecting road vector centerlines",
            what_it_proves="Quantifies physical centerline kilometers passing through the hazard zone.",
            what_it_does_not_prove="Exposure != disruption. Does NOT prove road closure, waterlogging, or pavement damage.",
            supported_component="EXPOSURE",
            permitted_wording=[
                "{length_km} kilometers of highway intersect the hazard boundary",
                "Linear transport exposure includes {length_km} km of road network",
            ],
            prohibited_wording=[
                "road closed",
                "highway blocked",
                "bridge collapsed",
                "impassable",
                "washout confirmed",
            ],
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="NHAI Highway Network 2024",
            geography="India",
            time_basis="Static Highway Layer",
            source_version="v1.0",
        ),

        # 4. Building Footprints
        ClaimRecord(
            claim_id="CLM-EXPOSURE-BLD-001",
            claim_text="Structural building footprints intersecting the hazard perimeter.",
            evidence_references=["SRC-MUNICIPAL-GIS"],
            applicability="Active hazard polygon intersecting building footprint polygons",
            what_it_proves="Quantifies number and footprint area (m²) of physical structures inside the hazard zone.",
            what_it_does_not_prove="Does NOT infer building occupancy, collapse risk, wall failure, or monetary damage.",
            supported_component="EXPOSURE",
            permitted_wording=[
                "{count} building structures intersect the hazard footprint",
                "Total exposed footprint area is {area_sqm} square meters",
            ],
            prohibited_wording=[
                "buildings collapsed",
                "roof blown off",
                "inundation damage",
                "uninhabitable",
                "total destruction",
            ],
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="Municipal Cadastral Survey",
            geography="India",
            time_basis="Municipal Cadastre 2024",
            source_version="v1.0",
        ),

        # 5. Agricultural Cropland & Farm Plots
        ClaimRecord(
            claim_id="CLM-EXPOSURE-AGRI-001",
            claim_text="Registered farm plots and cultivated acreage overlapping the hazard footprint.",
            evidence_references=["SRC-FARMER-REGISTRY"],
            applicability="Active hazard boundary intersecting registered agricultural plots",
            what_it_proves="Quantifies cultivated acreage geographically exposed to the hazard footprint.",
            what_it_does_not_prove="Does NOT estimate crop lodging, submergence mortality, yield reduction, or financial loss.",
            supported_component="EXPOSURE",
            permitted_wording=[
                "{acres} acres of cultivated cropland fall within the hazard boundary",
                "Identified {count} registered farm plots overlapping hazard perimeter",
            ],
            prohibited_wording=[
                "crop destroyed",
                "100% yield loss",
                "crop failure confirmed",
                "financial loss of",
            ],
            lifecycle_status=ClaimLifecycleStatus.APPROVED,
            exact_locator="VAYUBODHAK Farmer Registry",
            geography="India",
            time_basis="Seasonal Agricultural Register",
            source_version="v1.0",
        ),
    ]

    for c in claims:
        registry.register_claim(c)


# Auto-register on import
register_exposure_claims()

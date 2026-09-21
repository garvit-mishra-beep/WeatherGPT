"""Healthcare & Educational Critical Service Disruption Modeling for VAYUBODHAK Phase 7.

Implements:
- IMPACT-METH-SERV-HOSP-001: Healthcare facility operational capacity at risk prototype
- IMPACT-METH-SERV-SCHL-001: Educational facility operational disruption prototype

CRITICAL ETHICAL & SAFETY BOUNDARIES:
1. Physical Exposure != Service Shutdown: Facilities often maintain emergency continuity protocols.
2. Capacity At Risk != Casualties: Strictly does NOT estimate patient injuries, mortalities,
   or medical fatalities.
3. Facility Disruption != Student Harm: Strictly does NOT predict student injuries or deaths.
4. Does NOT issue hospital evacuation mandates or official school closure decrees.
"""

from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, Optional

from app.evidence.models import QualityState, SourceAuthorityLevel
from app.exposure.models import CriticalAsset, SpatialResolution
from app.impact.method_registry import impact_method_registry
from app.impact.models import (
    DamageState,
    ImpactType,
    ImpactUncertainty,
    PotentialImpactAssessment,
)
from app.vulnerability.models import MethodClassification


def evaluate_hospital_service_disruption(
    hazard_id: str,
    hazard_type: str,
    hazard_severity: str,
    hospital: CriticalAsset,
    access_road_disrupted: bool = False,
    exposure_id: Optional[str] = None,
    vulnerability_id: Optional[str] = None,
    risk_id: Optional[str] = None,
    source_id: str = "SRC-WHO-HSI",
    quality_state: QualityState = QualityState.VALID,
) -> PotentialImpactAssessment:
    """Evaluates operational capacity at risk and access strain for an exposed healthcare facility.
    
    Enforces:
    1. Operational Capacity at Risk != Patient Mortality: strictly measures inpatient beds
       potentially impacted by external transit/utility stress, NOT patient harm.
    2. Zero boundary: Severity NONE yields zero capacity at risk and DamageState.NONE.
    """
    method_id = "IMPACT-METH-SERV-HOSP-001"
    impact_method_registry.validate_method_active(method_id)

    sev_tier = hazard_severity.upper().strip()
    bed_capacity = float(hospital.metadata.get("bed_count", hospital.metadata.get("beds", 100)))

    if sev_tier == "NONE":
        damage_state = DamageState.NONE
        strain_ratio = 0.0
        capacity_at_risk = 0.0
        status_note = "Normal clinical operations; zero meteorological access strain"
    elif sev_tier in ["SEVERE", "EXTREME"] or (sev_tier == "WARNING" and access_road_disrupted):
        # Major service strain: emergency triage priority, ambulance rerouting
        damage_state = DamageState.MAJOR if sev_tier == "EXTREME" else DamageState.MODERATE
        strain_ratio = 0.80 if access_road_disrupted else 0.50
        capacity_at_risk = round(bed_capacity * strain_ratio, 0)
        status_note = "High external operational strain; emergency ambulance access and utility resilience stressed"
    elif sev_tier == "WARNING":
        damage_state = DamageState.MINOR
        strain_ratio = 0.25
        capacity_at_risk = round(bed_capacity * strain_ratio, 0)
        status_note = "Moderate external operational strain; facility remains operational under heightened alert"
    else:  # WATCH
        damage_state = DamageState.NONE
        strain_ratio = 0.05
        capacity_at_risk = round(bed_capacity * strain_ratio, 0)
        status_note = "Routine monitoring; baseline facility operations intact"

    uncertainty = ImpactUncertainty(
        methodology="Healthcare Facility Operational Capacity at Risk Prototype",
        spatial_resolution=SpatialResolution.POINT,
        assumptions=[
            f"Hospital registered bed capacity is {int(bed_capacity)} beds",
            "External severe flooding or road disruption impedes routine patient admissions and supply transit",
        ],
        limitations=[
            "Capacity At Risk != Casualties: Strictly does NOT model patient mortality, health harm, or disease",
            "On-site diesel generators, backup water cisterns, and rooftop helipads are unmodeled",
            "Does NOT issue official hospital evacuation orders or administrative patient diversion decrees",
        ],
        data_coverage=1.0 if "bed_count" in hospital.metadata or "beds" in hospital.metadata else 0.60,
        is_historical=False,
        prototype_dependency=True,
        method_classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
        source_basis_disclosure=(
            "WHO Hospital Safety Index and NDMA hospital safety guidelines establish institutional continuity and lifeline access principles (E1). "
            "The exact operational strain multipliers (5%, 25%, 50%, 80%) are VAYUBODHAK engineering prototype ratios, "
            "strictly excluding patient mortality, clinical morbidity, or healthcare worker harm."
        ),
        confidence_bounds={
            "lower_beds_at_risk": max(0.0, capacity_at_risk * 0.7),
            "upper_beds_at_risk": min(bed_capacity, capacity_at_risk * 1.3),
        } if capacity_at_risk > 0 else None,
        known_biases=["Assumes uniform operational vulnerability across hospital departments"],
        source_supported_parameters=[
            "WHO Hospital Safety Index operational dependency principles (RESEARCH-SUPPORTED CONCEPT)",
            "NDMA Hospital Safety Guidelines multi-hazard operational criteria (RESEARCH-SUPPORTED CONCEPT)",
        ],
        prototype_parameters=[
            f"Operational capacity strain ratio ({strain_ratio}) for {sev_tier} hazard (VAYUBODHAK prototype assumption)",
            "External access dependency amplification (50% to 80%) (VAYUBODHAK prototype assumption)",
        ],
        sensitivity_analysis={
            "access_road_impact": "Disruption of feeder roads escalates operational strain ratio from 0.50 to 0.80 under severe hazard",
            "auxiliary_power_buffer": "On-site backup generation buffers clinical operations for up to 48 hours without grid supply",
        },
    )

    prov_payload = f"{hazard_id}:{exposure_id}:{hospital.asset_id}:{sev_tier}:{access_road_disrupted}:{capacity_at_risk}"
    prov_hash = hashlib.sha256(prov_payload.encode()).hexdigest()
    impact_id = f"IMP-HOSP-{hospital.asset_id}-{prov_hash[:8]}"

    return PotentialImpactAssessment(
        impact_id=impact_id,
        hazard_id=hazard_id,
        exposure_id=exposure_id,
        vulnerability_id=vulnerability_id,
        risk_id=risk_id,
        impact_type=ImpactType.SERVICE_DISRUPTION,
        entity_type="HOSPITAL",
        entity_id=hospital.asset_id,
        damage_state=damage_state,
        damage_ratio=strain_ratio,
        affected_quantity=bed_capacity,
        disrupted_quantity=capacity_at_risk,
        unit="beds",
        duration_hours=24.0 if sev_tier in ["SEVERE", "EXTREME"] else 8.0 if sev_tier == "WARNING" else 0.0,
        economic_valuation=None,
        method_id=method_id,
        method_version="1.0.0",
        method_classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
        is_prototype=True,
        parameter_classification="VAYUBODHAK_PROTOTYPE_ASSUMPTION",
        prototype_disclosure=(
            "Prototype healthcare operational strain approximation; scenario-based consequence approximation, "
            "strictly does NOT model patient mortality or casualties"
        ),
        source_authority_level=SourceAuthorityLevel.E1,
        spatial_resolution=SpatialResolution.POINT,
        quality_state=quality_state,
        uncertainty=uncertainty,
        evidence_ids=[source_id],
        source_ids=[source_id],
        provenance_id=prov_hash,
        derived_from=[hazard_id, *([exposure_id] if exposure_id else []), *([vulnerability_id] if vulnerability_id else [])],
        details={
            "hospital_name": hospital.name,
            "total_bed_capacity": int(bed_capacity),
            "capacity_at_risk_beds": int(capacity_at_risk),
            "strain_ratio": strain_ratio,
            "access_road_disrupted": access_road_disrupted,
            "status_note": status_note,
        },
    )


def evaluate_school_service_disruption(
    hazard_id: str,
    hazard_type: str,
    hazard_severity: str,
    school: CriticalAsset,
    exposure_id: Optional[str] = None,
    vulnerability_id: Optional[str] = None,
    risk_id: Optional[str] = None,
    source_id: str = "SRC-NDMA-GUIDELINES",
    quality_state: QualityState = QualityState.VALID,
) -> PotentialImpactAssessment:
    """Evaluates operational continuity and shelter availability impact for an exposed school.
    
    Enforces:
    1. Operational Disruption != Student Casualties: strictly measures institutional availability,
       NOT physical harm or student injuries.
    2. Evaluates potential dual-use suitability as emergency relief shelter.
    """
    method_id = "IMPACT-METH-SERV-SCHL-001"
    impact_method_registry.validate_method_active(method_id)

    sev_tier = hazard_severity.upper().strip()
    enrollment = float(school.metadata.get("enrollment", 250))

    if sev_tier == "NONE":
        damage_state = DamageState.NONE
        disrupted = 0.0
        disruption_ratio = 0.0
        shelter_suitable = False
        status_note = "Standard academic operations active"
    elif sev_tier in ["SEVERE", "EXTREME"]:
        damage_state = DamageState.MAJOR
        disrupted = 1.0  # 1 facility disrupted
        disruption_ratio = 1.0
        shelter_suitable = True  # High potential for emergency shelter activation
        status_note = "Educational facility suspended; suitable for designated emergency shelter staging"
    elif sev_tier == "WARNING":
        damage_state = DamageState.MODERATE
        disrupted = 1.0
        disruption_ratio = 0.50
        shelter_suitable = True
        status_note = "Potential educational suspension; precautionary operational review indicated"
    else:  # WATCH
        damage_state = DamageState.MINOR
        disrupted = 0.0
        disruption_ratio = 0.0
        shelter_suitable = False
        status_note = "Heightened monitoring; operations proceed with caution"

    uncertainty = ImpactUncertainty(
        methodology="Educational Facility Operational Disruption Prototype",
        spatial_resolution=SpatialResolution.POINT,
        assumptions=[
            f"Facility registered student enrollment is {int(enrollment)}",
            "Administrative policy mandates suspension of academic sessions during official severe warnings",
        ],
        limitations=[
            "Facility Disruption != Student Harm: Strictly does NOT predict student injuries, casualties, or deaths",
            "Structural integrity of school buildings is unmodeled in service continuity calculation",
            "Does NOT issue administrative statutory school closure orders",
        ],
        data_coverage=1.0 if "enrollment" in school.metadata else 0.70,
        is_historical=False,
        prototype_dependency=True,
        method_classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
        source_basis_disclosure=(
            "NDMA School Safety Policy defines institutional continuity principles and disaster frameworks (E2). "
            "Exact facility operational suspension ratios (0.50, 1.0) and emergency shelter suitability indicators are "
            "VAYUBODHAK engineering prototype assessments, NOT statutory school closure decrees or facility-specific NDMA shelter certifications."
        ),
        known_biases=["Uniform operational assumption across primary/secondary tiers"],
        source_supported_parameters=[
            "NDMA School Safety Policy institutional disaster continuity guidelines (RESEARCH-SUPPORTED CONCEPT)",
            "National Disaster Management Plan school shelter dual-use policy framework (RESEARCH-SUPPORTED CONCEPT)",
        ],
        prototype_parameters=[
            f"Facility operational disruption indicator ({disrupted}) (VAYUBODHAK prototype assumption)",
            f"Operational suspension ratio ({disruption_ratio}) (VAYUBODHAK prototype assumption)",
            "Emergency relief shelter prototype suitability assessment (prototype heuristic; uncertified without facility-specific engineering audit)",
        ],
        sensitivity_analysis={
            "warning_tier_enforcement": "District administration discretion can trigger complete suspension at WARNING level, shifting disrupted facility count from 0 to 1",
            "shelter_intake_capacity": "Displaced community intake capacity depends on plinth area and WASH facilities rather than student enrollment",
        },
    )

    prov_payload = f"{hazard_id}:{exposure_id}:{school.asset_id}:{sev_tier}:{disrupted}"
    prov_hash = hashlib.sha256(prov_payload.encode()).hexdigest()
    impact_id = f"IMP-SCHL-{school.asset_id}-{prov_hash[:8]}"

    return PotentialImpactAssessment(
        impact_id=impact_id,
        hazard_id=hazard_id,
        exposure_id=exposure_id,
        vulnerability_id=vulnerability_id,
        risk_id=risk_id,
        impact_type=ImpactType.SERVICE_DISRUPTION,
        entity_type="SCHOOL",
        entity_id=school.asset_id,
        damage_state=damage_state,
        damage_ratio=disruption_ratio,
        affected_quantity=enrollment,
        disrupted_quantity=disrupted,
        unit="count",
        duration_hours=24.0 if sev_tier in ["SEVERE", "EXTREME"] else 12.0 if sev_tier == "WARNING" else 0.0,
        economic_valuation=None,
        method_id=method_id,
        method_version="1.0.0",
        method_classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
        is_prototype=True,
        parameter_classification="VAYUBODHAK_PROTOTYPE_ASSUMPTION",
        prototype_disclosure=(
            "Prototype educational service disruption approximation; scenario-based consequence approximation, "
            "strictly does NOT model student injuries or casualties"
        ),
        source_authority_level=SourceAuthorityLevel.E2,
        spatial_resolution=SpatialResolution.POINT,
        quality_state=quality_state,
        uncertainty=uncertainty,
        evidence_ids=[source_id],
        source_ids=[source_id],
        provenance_id=prov_hash,
        derived_from=[hazard_id, *([exposure_id] if exposure_id else []), *([vulnerability_id] if vulnerability_id else [])],
        details={
            "school_name": school.name,
            "enrollment": int(enrollment),
            "facility_disrupted": bool(disrupted > 0),
            "emergency_shelter_potential": shelter_suitable,
            "shelter_assessment_type": "PROTOTYPE_SUITABILITY_ASSESSMENT",
            "status_note": status_note,
        },
    )

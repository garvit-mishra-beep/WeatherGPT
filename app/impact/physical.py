"""Physical Structural Damage Modeling for VAYUBODHAK Phase 7.

Implements IMPACT-METH-PHYS-BLDG-001: Building structural damage state and damage ratio
estimation based on hazard severity, BMTPC structural typology, and vulnerability.

CRITICAL PRINCIPLES:
1. Exposure != Collapse. Damage state indicates potential physical degradation, not certain failure.
2. Zero-boundary condition: Zero hazard or zero vulnerability yields DamageState.NONE and 0.0 damage ratio.
3. Unclassified structural typologies return DamageState.UNDETERMINED with no fabricated ratios.
4. Strictly does NOT calculate occupant casualties or injuries.
"""

from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, Optional, Tuple

from app.evidence.models import QualityState, SourceAuthorityLevel
from app.exposure.models import BuildingFootprint, SpatialResolution
from app.impact.method_registry import impact_method_registry
from app.impact.models import (
    DamageState,
    ImpactType,
    ImpactUncertainty,
    PotentialImpactAssessment,
)
from app.vulnerability.models import BuildingStructuralClass, MethodClassification


# Damage Matrix: (StructuralClass, HazardSeverityTier) -> (DamageState, DamageRatio)
BUILDING_DAMAGE_MATRIX: Dict[Tuple[str, str], Tuple[DamageState, float]] = {
    # Kutcha (Mud / Thatch)
    ("KUTCHA_MUD_THATCH", "NONE"): (DamageState.NONE, 0.00),
    ("KUTCHA_MUD_THATCH", "WATCH"): (DamageState.MINOR, 0.10),
    ("KUTCHA_MUD_THATCH", "WARNING"): (DamageState.MODERATE, 0.35),
    ("KUTCHA_MUD_THATCH", "SEVERE"): (DamageState.MAJOR, 0.65),
    ("KUTCHA_MUD_THATCH", "EXTREME"): (DamageState.SEVERE, 0.90),

    # Semi-Pucca (Unburnt Brick / Mixed)
    ("SEMI_PUCCA_BRICK_UNBURNT", "NONE"): (DamageState.NONE, 0.00),
    ("SEMI_PUCCA_BRICK_UNBURNT", "WATCH"): (DamageState.NONE, 0.00),
    ("SEMI_PUCCA_BRICK_UNBURNT", "WARNING"): (DamageState.MINOR, 0.15),
    ("SEMI_PUCCA_BRICK_UNBURNT", "SEVERE"): (DamageState.MODERATE, 0.40),
    ("SEMI_PUCCA_BRICK_UNBURNT", "EXTREME"): (DamageState.MAJOR, 0.70),

    # Pucca (Burnt Brick / Masonry)
    ("PUCCA_BRICK_BURNT", "NONE"): (DamageState.NONE, 0.00),
    ("PUCCA_BRICK_BURNT", "WATCH"): (DamageState.NONE, 0.00),
    ("PUCCA_BRICK_BURNT", "WARNING"): (DamageState.NONE, 0.05),
    ("PUCCA_BRICK_BURNT", "SEVERE"): (DamageState.MINOR, 0.20),
    ("PUCCA_BRICK_BURNT", "EXTREME"): (DamageState.MODERATE, 0.45),

    # Pucca RCC
    ("PUCCA_RCC", "NONE"): (DamageState.NONE, 0.00),
    ("PUCCA_RCC", "WATCH"): (DamageState.NONE, 0.00),
    ("PUCCA_RCC", "WARNING"): (DamageState.NONE, 0.02),
    ("PUCCA_RCC", "SEVERE"): (DamageState.MINOR, 0.10),
    ("PUCCA_RCC", "EXTREME"): (DamageState.MODERATE, 0.25),

    # Steel Frame
    ("STEEL_FRAME", "NONE"): (DamageState.NONE, 0.00),
    ("STEEL_FRAME", "WATCH"): (DamageState.NONE, 0.00),
    ("STEEL_FRAME", "WARNING"): (DamageState.NONE, 0.02),
    ("STEEL_FRAME", "SEVERE"): (DamageState.MINOR, 0.10),
    ("STEEL_FRAME", "EXTREME"): (DamageState.MODERATE, 0.20),
}


def evaluate_building_physical_damage(
    hazard_id: str,
    hazard_type: str,
    hazard_severity: str,
    building: BuildingFootprint,
    structural_class: Optional[BuildingStructuralClass] = None,
    vulnerability_score: Optional[float] = None,
    exposure_id: Optional[str] = None,
    vulnerability_id: Optional[str] = None,
    risk_id: Optional[str] = None,
    source_id: str = "SRC-BMTPC-ATLAS",
    quality_state: QualityState = QualityState.VALID,
) -> PotentialImpactAssessment:
    """Evaluates potential physical structural damage for an exposed building.
    
    Enforces:
    1. Zero boundary: Hazard NONE or vulnerability 0.0 yields DamageState.NONE and ratio 0.0.
    2. Typology gating: Missing construction materials yields DamageState.UNDETERMINED.
    3. Structural damage ratio is bounded in [0.0, 1.0].
    4. Negative boundary: Zero casualty modeling, zero evacuation directives.
    """
    method_id = "IMPACT-METH-PHYS-BLDG-001"
    impact_method_registry.validate_method_active(method_id)

    sev_tier = hazard_severity.upper().strip()
    
    # Resolve structural typology
    s_class = structural_class
    if s_class is None:
        s_str = getattr(building, "structural_class", None)
        if s_str and s_str in BuildingStructuralClass.__members__:
            s_class = BuildingStructuralClass(s_str)
        else:
            s_class = BuildingStructuralClass.UNSPECIFIED

    # Check for missing structural class
    if s_class == BuildingStructuralClass.UNSPECIFIED:
        uncertainty = ImpactUncertainty(
            methodology="BMTPC Typology Building Physical Damage State & Ratio Prototype",
            spatial_resolution=SpatialResolution.BUILDING_FOOTPRINT,
            assumptions=["Building footprint geometry lacks construction typology attribution"],
            limitations=["Structural damage state cannot be inferred without structural material survey"],
            data_coverage=0.0,
            is_historical=False,
            prototype_dependency=True,
            method_classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
            source_basis_disclosure=(
                "BMTPC Vulnerability Atlas defines typologies (E2). "
                "Damage ratio estimation requires structural class; returns UNDETERMINED when unrecorded."
            ),
            known_biases=["Missing structural survey"],
        )
        impact_id = f"IMP-PHYS-{building.building_id}-UNDET"
        prov_hash = hashlib.sha256(f"{impact_id}:UNDETERMINED".encode()).hexdigest()
        
        return PotentialImpactAssessment(
            impact_id=impact_id,
            hazard_id=hazard_id,
            exposure_id=exposure_id,
            vulnerability_id=vulnerability_id,
            risk_id=risk_id,
            impact_type=ImpactType.PHYSICAL_DAMAGE,
            entity_type="BUILDING",
            entity_id=building.building_id,
            damage_state=DamageState.UNDETERMINED,
            damage_ratio=None,
            affected_quantity=building.footprint_area_sqm,
            disrupted_quantity=None,
            unit="sqm",
            economic_valuation=None,
            method_id=method_id,
            method_version="1.0.0",
            method_classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
            is_prototype=True,
            source_authority_level=SourceAuthorityLevel.E2,
            spatial_resolution=SpatialResolution.BUILDING_FOOTPRINT,
            quality_state=QualityState.MISSING,
            uncertainty=uncertainty,
            evidence_ids=[source_id],
            source_ids=[source_id],
            provenance_id=prov_hash,
            derived_from=[hazard_id, *([exposure_id] if exposure_id else []), *([vulnerability_id] if vulnerability_id else [])],
            details={"structural_class": "UNSPECIFIED", "status": "UNDETERMINED"},
        )

    # Zero boundary check
    if sev_tier == "NONE" or (vulnerability_score is not None and vulnerability_score == 0.0):
        damage_state = DamageState.NONE
        damage_ratio = 0.00
    else:
        lookup_key = (s_class.value, sev_tier)
        if lookup_key in BUILDING_DAMAGE_MATRIX:
            damage_state, damage_ratio = BUILDING_DAMAGE_MATRIX[lookup_key]
        else:
            damage_state = DamageState.MINOR
            damage_ratio = 0.10

    # Scale damage ratio by vulnerability score if present (calibration heuristic)
    if vulnerability_score is not None and damage_ratio > 0.0:
        damage_ratio = round(min(1.0, max(0.0, damage_ratio * (0.5 + 0.5 * vulnerability_score))), 3)

    uncertainty = ImpactUncertainty(
        methodology="BMTPC Typology Building Physical Damage State & Ratio Prototype",
        spatial_resolution=SpatialResolution.BUILDING_FOOTPRINT,
        assumptions=[
            f"Building construction adheres to BMTPC standard archetype for {s_class.value}",
            "Damage ratio reflects potential physical structural degradation relative to total replacement",
        ],
        limitations=[
            "Exposure != Collapse: Categorical damage state does not indicate imminent structural failure",
            "Foundation condition, age, unpermitted additions, and maintenance are unmodeled",
            "Software test coverage validates matrix execution, NOT empirical damage calibration",
        ],
        data_coverage=1.0,
        is_historical=False,
        prototype_dependency=True,
        method_classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
        source_basis_disclosure=(
            "BMTPC Vulnerability Atlas and NBC 2016 provide structural typology and contextual vulnerability information (E2). "
            "The discrete damage ratios (0.02, 0.10, 0.25, 0.50, 0.90) used by VAYUBODHAK are prototype engineering heuristic parameters, "
            "not empirically calibrated fragility curves or post-disaster insurance loss curves."
        ),
        confidence_bounds={
            "lower_damage_ratio": max(0.0, damage_ratio - 0.10),
            "upper_damage_ratio": min(1.0, damage_ratio + 0.15),
        } if damage_ratio > 0.0 else None,
        known_biases=["Archetype uniform assumption"],
        source_supported_parameters=[
            "BMTPC Vulnerability Atlas building typology definitions (Kutcha, Semi-Pucca, Pucca, Steel Frame) (SOURCE-SUPPORTED INPUT TYPOLOGY)",
            "NBC 2016 building construction classification and vulnerability context (SOURCE-SUPPORTED STANDARD)",
        ],
        prototype_parameters=[
            f"Building discrete damage ratio ({damage_ratio}) for {s_class.value} under {sev_tier} hazard (VAYUBODHAK prototype assumption; not an empirical fragility curve)",
            f"Categorical damage state ({damage_state.value}) mapping (VAYUBODHAK prototype heuristic)",
        ],
        sensitivity_analysis={
            "damage_ratio_elasticity": "Direct replacement cost scales linearly with damage ratio; a +/- 0.05 shift varies direct loss by +/- 5% of total replacement value",
            "typology_misclassification_risk": "Misidentifying Pucca RCC as Semi-Pucca increases modeled damage ratio by up to 0.45 under extreme hazard",
        },
    )

    prov_payload = f"{hazard_id}:{exposure_id}:{vulnerability_id}:{building.building_id}:{s_class.value}:{sev_tier}:{damage_ratio}"
    prov_hash = hashlib.sha256(prov_payload.encode()).hexdigest()
    impact_id = f"IMP-PHYS-{building.building_id}-{prov_hash[:8]}"

    return PotentialImpactAssessment(
        impact_id=impact_id,
        hazard_id=hazard_id,
        exposure_id=exposure_id,
        vulnerability_id=vulnerability_id,
        risk_id=risk_id,
        impact_type=ImpactType.PHYSICAL_DAMAGE,
        entity_type="BUILDING",
        entity_id=building.building_id,
        damage_state=damage_state,
        damage_ratio=damage_ratio,
        affected_quantity=building.footprint_area_sqm,
        disrupted_quantity=round(building.footprint_area_sqm * damage_ratio, 1) if damage_ratio else 0.0,
        unit="sqm",
        economic_valuation=None,
        method_id=method_id,
        method_version="1.0.0",
        method_classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
        is_prototype=True,
        parameter_classification="VAYUBODHAK_PROTOTYPE_ASSUMPTION",
        prototype_disclosure=(
            "Prototype building physical damage approximation based on BMTPC typology archetypes; "
            "scenario-based consequence approximation, not an empirical fragility curve; software-verified, not empirically loss-calibrated"
        ),
        source_authority_level=SourceAuthorityLevel.E2,
        spatial_resolution=SpatialResolution.BUILDING_FOOTPRINT,
        quality_state=quality_state,
        uncertainty=uncertainty,
        evidence_ids=[source_id],
        source_ids=[source_id],
        provenance_id=prov_hash,
        derived_from=[hazard_id, *([exposure_id] if exposure_id else []), *([vulnerability_id] if vulnerability_id else [])],
        details={
            "structural_class": s_class.value,
            "hazard_severity": sev_tier,
            "footprint_area_sqm": building.footprint_area_sqm,
            "damage_state": damage_state.value,
            "damage_ratio": damage_ratio,
        },
    )

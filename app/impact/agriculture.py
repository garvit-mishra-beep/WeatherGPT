"""Agricultural Phenological Yield Consequence Modeling for VAYUBODHAK Phase 7.

Implements IMPACT-METH-AGRI-YIELD-001: Crop phenological yield loss percentage and
estimated production consequence modeling based on growth stage susceptibility and hazard intensity.

CRITICAL DISTINCTIONS & PRINCIPLES:
1. Crop Exposure != Susceptibility != Yield Loss. Exposure is planted acreage; susceptibility
   is physiological vulnerability; yield loss is the consequence modeled here under an explicit function.
2. Passing software tests does NOT scientifically validate crop physiological damage curves.
   This model is explicitly classified as VAYUBODHAK_PROTOTYPE.
3. Does NOT calculate crop insurance payouts or predict farmer economic distress.
"""

from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, Optional, Tuple

from app.evidence.models import QualityState, SourceAuthorityLevel
from app.exposure.models import SpatialResolution
from app.impact.method_registry import impact_method_registry
from app.impact.models import (
    DamageState,
    ImpactType,
    ImpactUncertainty,
    PotentialImpactAssessment,
)
from app.vulnerability.models import CropGrowthStage, MethodClassification


# Phenological Yield Sensitivity Factors: (GrowthStage, HazardSeverityTier) -> (DamageState, BaseYieldLossPct)
YIELD_LOSS_MATRIX: Dict[Tuple[str, str], Tuple[DamageState, float]] = {
    # Germination / Emergence
    ("GERMINATION", "NONE"): (DamageState.NONE, 0.00),
    ("GERMINATION", "WATCH"): (DamageState.NONE, 0.05),
    ("GERMINATION", "WARNING"): (DamageState.MINOR, 0.20),
    ("GERMINATION", "SEVERE"): (DamageState.MODERATE, 0.45),
    ("GERMINATION", "EXTREME"): (DamageState.MAJOR, 0.70),

    # Vegetative
    ("VEGETATIVE", "NONE"): (DamageState.NONE, 0.00),
    ("VEGETATIVE", "WATCH"): (DamageState.NONE, 0.02),
    ("VEGETATIVE", "WARNING"): (DamageState.MINOR, 0.10),
    ("VEGETATIVE", "SEVERE"): (DamageState.MODERATE, 0.30),
    ("VEGETATIVE", "EXTREME"): (DamageState.MAJOR, 0.55),

    # Flowering / Anthesis (Critical Stage)
    ("FLOWERING", "NONE"): (DamageState.NONE, 0.00),
    ("FLOWERING", "WATCH"): (DamageState.MINOR, 0.10),
    ("FLOWERING", "WARNING"): (DamageState.MODERATE, 0.40),
    ("FLOWERING", "SEVERE"): (DamageState.MAJOR, 0.75),
    ("FLOWERING", "EXTREME"): (DamageState.SEVERE, 0.90),

    # Maturity / Harvesting
    ("MATURITY_HARVESTING", "NONE"): (DamageState.NONE, 0.00),
    ("MATURITY_HARVESTING", "WATCH"): (DamageState.NONE, 0.05),
    ("MATURITY_HARVESTING", "WARNING"): (DamageState.MODERATE, 0.35),
    ("MATURITY_HARVESTING", "SEVERE"): (DamageState.MAJOR, 0.70),
    ("MATURITY_HARVESTING", "EXTREME"): (DamageState.SEVERE, 0.85),
}


def evaluate_agricultural_yield_impact(
    hazard_id: str,
    hazard_type: str,
    hazard_severity: str,
    crop_name: str,
    growth_stage: CropGrowthStage,
    planted_acres: float,
    baseline_yield_tonnes_per_acre: float = 1.5,
    vulnerability_score: Optional[float] = None,
    plot_id: Optional[str] = None,
    exposure_id: Optional[str] = None,
    vulnerability_id: Optional[str] = None,
    risk_id: Optional[str] = None,
    source_id: str = "SRC-ICAR-ADVISORIES",
    quality_state: QualityState = QualityState.VALID,
) -> PotentialImpactAssessment:
    """Evaluates potential agricultural yield loss percentage and production deficit.
    
    Enforces:
    1. Exposure != Susceptibility != Yield Loss: Explicit function connects stage sensitivity
       and hazard tier into an estimated yield loss ratio.
    2. Zero boundary: Severity NONE yields 0.0 yield loss and 0.0 production loss tonnes.
    3. Production loss is in metric tonnes, planted area in acres.
    """
    method_id = "IMPACT-METH-AGRI-YIELD-001"
    impact_method_registry.validate_method_active(method_id)

    sev_tier = hazard_severity.upper().strip()
    stage_str = growth_stage.value
    acres = max(0.0, round(planted_acres, 2))
    expected_total_production_tonnes = round(acres * baseline_yield_tonnes_per_acre, 2)

    # Zero boundary check
    if sev_tier == "NONE" or (vulnerability_score is not None and vulnerability_score == 0.0) or acres == 0.0:
        damage_state = DamageState.NONE
        yield_loss_ratio = 0.00
        production_loss_tonnes = 0.00
        status_note = "Normal physiological crop growth; zero meteorological yield loss"
    else:
        lookup_key = (stage_str, sev_tier)
        if lookup_key in YIELD_LOSS_MATRIX:
            damage_state, base_loss_ratio = YIELD_LOSS_MATRIX[lookup_key]
        else:
            damage_state = DamageState.MODERATE
            base_loss_ratio = 0.30

        # Adjust by vulnerability score if present
        if vulnerability_score is not None and base_loss_ratio > 0.0:
            yield_loss_ratio = round(min(1.0, max(0.0, base_loss_ratio * (0.6 + 0.4 * vulnerability_score))), 3)
        else:
            yield_loss_ratio = base_loss_ratio

        production_loss_tonnes = round(expected_total_production_tonnes * yield_loss_ratio, 2)
        status_note = f"Estimated {round(yield_loss_ratio * 100, 1)}% yield deficit due to {sev_tier} {hazard_type} during {stage_str}"

    uncertainty = ImpactUncertainty(
        methodology="Crop Phenological Yield Consequence Prototype",
        spatial_resolution=SpatialResolution.ADMINISTRATIVE_POLYGON,
        assumptions=[
            f"Planted crop is {crop_name} across {acres} acres",
            f"Phenological growth stage is verified as {stage_str}",
            f"Baseline expected normal yield is {baseline_yield_tonnes_per_acre} tonnes/acre",
        ],
        limitations=[
            "Exposure != Crop Failure: Phenological loss percentage does not guarantee total crop destruction",
            "Cultivar genetic resilience, soil nutrient status, and post-event agronomic rescue are unmodeled",
            "Does NOT calculate crop insurance payouts or government relief compensation eligibility",
        ],
        data_coverage=1.0,
        is_historical=False,
        prototype_dependency=True,
        method_classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
        source_basis_disclosure=(
            "ICAR and FAO-56 agromet advisories identify phenological critical stages and physiological sensitivity principles (E1). "
            "The discrete yield loss percentage mapping (including the 0.90 extreme flowering parameter) is a VAYUBODHAK engineering "
            "prototype assumption, NOT a universal ICAR/FAO yield-loss equation or biophysical dynamic crop simulation (e.g. DSSAT). "
            "Actual yield response varies with crop species, cultivar, stress intensity, stress duration, soil/water conditions, management, and environmental context."
        ),
        confidence_bounds={
            "min_loss_pct": max(0.0, yield_loss_ratio * 0.75),
            "max_loss_pct": min(1.0, yield_loss_ratio * 1.25),
        } if yield_loss_ratio > 0 else None,
        known_biases=["Uniform plot-level elevation and drainage assumption"],
        source_supported_parameters=[
            "ICAR Agromet Advisory phenological stage definitions (Germination, Vegetative, Flowering/Anthesis, Maturity) (SOURCE-SUPPORTED INPUT CONCEPT)",
            "FAO-56 and FAO Paper 66 crop yield response principles and stage sensitivity concepts (RESEARCH-SUPPORTED CONCEPT)",
        ],
        prototype_parameters=[
            f"Phenological yield loss deficit ratio ({yield_loss_ratio * 100:.1f}%) for {stage_str} under {sev_tier} hazard (VAYUBODHAK prototype assumption; not a universal equation)",
            f"Assumed baseline normal yield ({baseline_yield_tonnes_per_acre} tonnes/acre) (prototype baseline assumption)",
        ],
        sensitivity_analysis={
            "anthesis_physiological_sensitivity": (
                "Anthesis/flowering is a scientifically recognized sensitive phenological bottleneck for several crops; "
                "severe thermal stress or prolonged submergence significantly impairs pollination and induces substantial spikelet sterility. "
                "The exact 0.90 yield-deficit parameter is a VAYUBODHAK prototype engineering assumption and not a universal ICAR/FAO yield-loss equation. "
                "Actual response varies with crop species, cultivar tolerance, stress duration, soil/water conditions, and management."
            ),
            "cultivar_tolerance_variation": "Submergence-tolerant cultivars or heat-tolerant lines exhibit lower yield deficits relative to standard archetype assumptions",
        },
    )

    entity_id = plot_id or f"AGRI-{crop_name}-{stage_str}"
    prov_payload = f"{hazard_id}:{exposure_id}:{vulnerability_id}:{entity_id}:{stage_str}:{sev_tier}:{yield_loss_ratio}"
    prov_hash = hashlib.sha256(prov_payload.encode()).hexdigest()
    impact_id = f"IMP-AGRI-{crop_name[:4]}-{prov_hash[:8]}"

    return PotentialImpactAssessment(
        impact_id=impact_id,
        hazard_id=hazard_id,
        exposure_id=exposure_id,
        vulnerability_id=vulnerability_id,
        risk_id=risk_id,
        impact_type=ImpactType.AGRICULTURAL_IMPACT,
        entity_type="AGRICULTURE",
        entity_id=entity_id,
        damage_state=damage_state,
        damage_ratio=yield_loss_ratio,
        affected_quantity=acres,
        disrupted_quantity=production_loss_tonnes,
        unit="acres",
        economic_valuation=None,
        method_id=method_id,
        method_version="1.0.0",
        method_classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
        is_prototype=True,
        parameter_classification="VAYUBODHAK_PROTOTYPE_ASSUMPTION",
        prototype_disclosure=(
            "Prototype agricultural phenological yield loss approximation; scenario-based consequence approximation, "
            "not calibrated against biophysical crop models (DSSAT) or PMFBY insurance claims; not a universal equation"
        ),
        source_authority_level=SourceAuthorityLevel.E1,
        spatial_resolution=SpatialResolution.ADMINISTRATIVE_POLYGON,
        quality_state=quality_state,
        uncertainty=uncertainty,
        evidence_ids=[source_id],
        source_ids=[source_id],
        provenance_id=prov_hash,
        derived_from=[hazard_id, *([exposure_id] if exposure_id else []), *([vulnerability_id] if vulnerability_id else [])],
        details={
            "crop_name": crop_name,
            "growth_stage": stage_str,
            "planted_acres": acres,
            "baseline_yield_tonnes_per_acre": baseline_yield_tonnes_per_acre,
            "expected_production_tonnes": expected_total_production_tonnes,
            "potential_yield_loss_pct": round(yield_loss_ratio * 100.0, 1),
            "estimated_production_loss_tonnes": production_loss_tonnes,
            "status_note": status_note,
        },
    )

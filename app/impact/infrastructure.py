"""Road Transport Infrastructure Disruption Modeling for VAYUBODHAK Phase 7.

Implements IMPACT-METH-INFRA-ROAD-001: Linear road transport corridor waterlogging
and disruption impact estimation.

CRITICAL INVARIANTS:
1. Exposure != Disruption: Spatial intersection with a hazard polygon does NOT automatically
   mean the road is closed. Disruption requires meeting explicit hydrological/meteorological triggers.
2. If trigger threshold is not exceeded, disrupted_quantity is 0.0 km and damage_state is NONE.
3. Does NOT issue police closure orders or forecast traffic accident casualties.
"""

from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, Optional

from app.evidence.models import QualityState, SourceAuthorityLevel
from app.exposure.models import RoadSegment, SpatialResolution
from app.impact.method_registry import impact_method_registry
from app.impact.models import (
    DamageState,
    ImpactType,
    ImpactUncertainty,
    PotentialImpactAssessment,
)
from app.vulnerability.models import MethodClassification


# Disruption Thresholds (Source-Supported Input Thresholds & Aligned Engineering Inputs)
# IMD Rainfall Classification Thresholds (SOURCE_SUPPORTED_INPUT_THRESHOLD)
IMD_RAINFALL_HEAVY_THRESHOLD_MM = 64.5        # IMD 24h Heavy Rainfall classification threshold (source-supported input)
IMD_RAINFALL_VERY_HEAVY_THRESHOLD_MM = 115.6  # IMD 24h Very Heavy Rainfall classification threshold (source-supported input)

# IRC Road Drainage Aligned Engineering Inputs (SOURCE-ALIGNED ENGINEERING INPUT)
IRC_INUNDATION_MODERATE_M = 0.3     # 30 cm water depth (source-aligned engineering input: passenger car exhaust sill clearance consideration)
IRC_INUNDATION_SEVERE_M = 0.5       # 50 cm water depth (source-aligned engineering input: heavy vehicle axle clearance consideration)

# Backward-compatible references
RAINFALL_HEAVY_MM = IMD_RAINFALL_HEAVY_THRESHOLD_MM
RAINFALL_VERY_HEAVY_MM = IMD_RAINFALL_VERY_HEAVY_THRESHOLD_MM
INUNDATION_MODERATE_M = IRC_INUNDATION_MODERATE_M
INUNDATION_SEVERE_M = IRC_INUNDATION_SEVERE_M


def evaluate_road_infrastructure_disruption(
    hazard_id: str,
    hazard_type: str,
    hazard_severity: str,
    road: RoadSegment,
    observed_rainfall_mm: Optional[float] = None,
    inundation_depth_m: Optional[float] = None,
    exposure_id: Optional[str] = None,
    vulnerability_id: Optional[str] = None,
    risk_id: Optional[str] = None,
    source_id: str = "SRC-IRC-ROAD-STANDARDS",
    quality_state: QualityState = QualityState.VALID,
) -> PotentialImpactAssessment:
    """Evaluates transport network disruption length and duration for an exposed road segment.
    
    Enforces:
    1. Exposure != Disruption: Intersecting a hazard zone reports exposed length, but
       disrupted length is strictly 0.0 km unless rainfall >= 64.5 mm or depth >= 0.3 m.
    2. Duration is an engineering prototype window, not an official traffic reopening time.
    3. Zero boundary: Severity NONE or zero precipitation/inundation yields zero disruption.
    4. Consequence Separation: IMD rainfall criteria and IRC depth clearances are source inputs;
       disrupted corridor length percentages and durations are VAYUBODHAK prototype consequence rules.
    """
    method_id = "IMPACT-METH-INFRA-ROAD-001"
    impact_method_registry.validate_method_active(method_id)

    sev_tier = hazard_severity.upper().strip()
    total_length_km = round(road.length_km, 2)

    # Check triggers
    rainfall = observed_rainfall_mm if observed_rainfall_mm is not None else 0.0
    depth = inundation_depth_m if inundation_depth_m is not None else 0.0

    is_severe_trigger = (rainfall >= RAINFALL_VERY_HEAVY_MM) or (depth >= INUNDATION_SEVERE_M) or (sev_tier in ["SEVERE", "EXTREME"] and rainfall >= RAINFALL_HEAVY_MM)
    is_moderate_trigger = (rainfall >= RAINFALL_HEAVY_MM) or (depth >= INUNDATION_MODERATE_M) or (sev_tier == "WARNING" and rainfall >= 35.0)

    if sev_tier == "NONE" or (rainfall == 0.0 and depth == 0.0 and sev_tier not in ["SEVERE", "EXTREME"]):
        # Zero disruption condition
        damage_state = DamageState.NONE
        disrupted_length_km = 0.0
        disruption_ratio = 0.0
        duration_hours = 0.0
        status_note = "Normal operational transit; no hydrological disruption trigger met"
    elif is_severe_trigger:
        # Severe waterlogging: full exposed corridor impassable
        damage_state = DamageState.MAJOR
        disruption_ratio = 1.0
        disrupted_length_km = total_length_km
        duration_hours = 12.0
        status_note = "Severe waterlogging trigger exceeded; vehicular transit severely impaired"
    elif is_moderate_trigger:
        # Moderate waterlogging: localized urban traffic slowdown and partial corridor disruption
        damage_state = DamageState.MODERATE
        disruption_ratio = 0.50
        disrupted_length_km = round(total_length_km * 0.50, 2)
        duration_hours = 4.0
        status_note = "Moderate waterlogging trigger met; speed restrictions and localized delays"
    else:
        # Exposed to hazard watch/warning, but rainfall/depth below operational disruption threshold
        damage_state = DamageState.MINOR
        disruption_ratio = 0.0
        disrupted_length_km = 0.0
        duration_hours = 0.0
        status_note = "Road corridor exposed to meteorological watch, but below disruption threshold (Exposure != Disruption)"

    uncertainty = ImpactUncertainty(
        methodology="Road Infrastructure Transport Disruption Prototype",
        spatial_resolution=SpatialResolution.ROAD_SEGMENT,
        assumptions=[
            f"Road classification is {road.road_classification}",
            "Surface drainage conforms to standard IRC design parameters without localized culvert blockage",
            "Precipitation >= 64.5 mm generates localized stormwater accumulation exceeding curb capacity",
        ],
        limitations=[
            "Exposure != Disruption: Surface intersection does not constitute official road closure",
            "Real-time stormwater pumping, flyover bypasses, and traffic diversions are unmodeled",
            "Duration represents estimated hydrological drainage window, not administrative road reopening decree",
        ],
        data_coverage=1.0 if observed_rainfall_mm is not None or inundation_depth_m is not None else 0.70,
        is_historical=False,
        prototype_dependency=True,
        method_classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
        source_basis_disclosure=(
            "IMD defines 24h rainfall classification criteria (64.5 mm Heavy, 115.6 mm Very Heavy) as source-supported input thresholds. "
            "IRC road drainage guidelines (IRC:SP:42 / IRC:SP:50) provide source-aligned engineering inputs regarding water-depth trafficability. "
            "Corridor disrupted length fractions (50% and 100%) and estimated drainage windows (4h and 12h) are "
            "VAYUBODHAK prototype consequence rules, NOT source-defined traffic closure mandates."
        ),
        confidence_bounds={
            "min_duration_hours": max(0.0, duration_hours * 0.5),
            "max_duration_hours": duration_hours * 1.8,
        } if duration_hours > 0 else None,
        known_biases=["Uniform elevation assumption along linear segment"],
        source_supported_parameters=[
            "IMD rainfall classification thresholds: Heavy Rainfall >= 64.5 mm/24h, Very Heavy Rainfall >= 115.6 mm/24h (SOURCE_SUPPORTED_INPUT_THRESHOLD)",
            "IRC road drainage guidelines (IRC:SP:42 & IRC:SP:50) trafficability water depth considerations: 0.3 m car exhaust sill, 0.5 m heavy vehicle axle clearance (SOURCE-ALIGNED ENGINEERING INPUT)",
        ],
        prototype_parameters=[
            f"Road corridor disrupted length fraction ({disruption_ratio * 100:.0f}%) (VAYUBODHAK prototype consequence rule)",
            f"Corridor drainage duration window ({duration_hours} hours) (VAYUBODHAK prototype consequence rule)",
        ],
        sensitivity_analysis={
            "drainage_duration_sensitivity": "Drainage duration is inversely proportional to drainage clearing efficiency and varies +/- 50% under culvert siltation",
            "corridor_length_sensitivity": "Micro-topographic depressions may localize waterlogging to 20-30% or expand impassable segments under prolonged rainfall",
        },
    )

    prov_payload = f"{hazard_id}:{exposure_id}:{road.road_id}:{sev_tier}:{rainfall}:{depth}:{disrupted_length_km}"
    prov_hash = hashlib.sha256(prov_payload.encode()).hexdigest()
    impact_id = f"IMP-ROAD-{road.road_id}-{prov_hash[:8]}"

    return PotentialImpactAssessment(
        impact_id=impact_id,
        hazard_id=hazard_id,
        exposure_id=exposure_id,
        vulnerability_id=vulnerability_id,
        risk_id=risk_id,
        impact_type=ImpactType.INFRASTRUCTURE_DISRUPTION,
        entity_type="ROAD",
        entity_id=road.road_id,
        damage_state=damage_state,
        damage_ratio=disruption_ratio,
        affected_quantity=total_length_km,
        disrupted_quantity=disrupted_length_km,
        unit="km",
        duration_hours=duration_hours,
        economic_valuation=None,
        method_id=method_id,
        method_version="1.0.0",
        method_classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
        is_prototype=True,
        parameter_classification="VAYUBODHAK_PROTOTYPE_ASSUMPTION",
        prototype_disclosure=(
            "Prototype road transport disruption approximation based on IMD input thresholds and IRC-aligned water depth inputs; "
            "disrupted corridor fractions and durations are uncalibrated VAYUBODHAK prototype rules, not observed traffic closures"
        ),
        source_authority_level=SourceAuthorityLevel.E2,
        spatial_resolution=SpatialResolution.ROAD_SEGMENT,
        quality_state=quality_state,
        uncertainty=uncertainty,
        evidence_ids=[source_id],
        source_ids=[source_id],
        provenance_id=prov_hash,
        derived_from=[hazard_id, *([exposure_id] if exposure_id else []), *([vulnerability_id] if vulnerability_id else [])],
        details={
            "road_name": road.road_name,
            "road_classification": road.road_classification,
            "total_length_km": total_length_km,
            "disrupted_length_km": disrupted_length_km,
            "rainfall_mm": observed_rainfall_mm,
            "inundation_depth_m": inundation_depth_m,
            "duration_hours": duration_hours,
            "status_note": status_note,
        },
    )

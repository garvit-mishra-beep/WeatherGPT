"""Potential Impact Engine for VAYUBODHAK Phase 7.

Orchestrates deterministic potential impact assessments across physical structures,
road infrastructure, healthcare/education lifelines, agriculture, and direct economic loss.

CRITICAL INVARIANTS:
1. Exposure: What is there.
2. Vulnerability: How susceptible it is.
3. Risk: Relative prototype index (Phase 6).
4. Potential Impact: Estimated consequence under an explicit, bounded impact model.
5. NO casualty or fatality prediction.
6. NO evacuation order, relief prioritization, or rescue dispatch.
7. NO LLM-generated impact calculations (100% deterministic Python logic).
"""

from datetime import datetime, timezone
import hashlib
import uuid
from typing import Any, Dict, List, Optional

from app.evidence.claim_gate import claim_registry
from app.evidence.models import QualityState
from app.exposure.models import BuildingFootprint, CriticalAsset, RoadSegment
from app.hazard.models import HazardEvaluation, HazardState
from app.impact.agriculture import evaluate_agricultural_yield_impact
from app.impact.claims import register_impact_claims
from app.impact.economic import evaluate_direct_economic_loss
from app.impact.infrastructure import evaluate_road_infrastructure_disruption
from app.impact.method_registry import impact_method_registry
from app.impact.models import (
    DamageState,
    ImpactEvaluationBundle,
    ImpactType,
    PotentialImpactAssessment,
)
from app.impact.physical import evaluate_building_physical_damage
from app.impact.service import (
    evaluate_hospital_service_disruption,
    evaluate_school_service_disruption,
)
from app.risk.models import RiskAssessment
from app.vulnerability.models import BuildingStructuralClass, CropGrowthStage, VulnerabilityResult


def _get_hazard_id(hazard: HazardEvaluation) -> str:
    return getattr(hazard, "hazard_id", None) or getattr(hazard, "evaluation_id", "HZD-UNKNOWN")


def _get_hazard_type_str(hazard: HazardEvaluation) -> str:
    ht = getattr(hazard, "hazard_type", "UNKNOWN")
    return ht.value if hasattr(ht, "value") else str(ht)


def _get_hazard_state_str(hazard: HazardEvaluation) -> str:
    st = getattr(hazard, "hazard_state", None) or getattr(hazard, "state", "NONE")
    return st.value if hasattr(st, "value") else str(st)


def _get_quality_state(hazard: HazardEvaluation) -> QualityState:
    qs = getattr(hazard, "quality_state", QualityState.VALID)
    if isinstance(qs, QualityState):
        return qs
    try:
        return QualityState(str(qs).upper())
    except ValueError:
        return QualityState.VALID


class ImpactEngine:
    """Deterministic orchestrator for VAYUBODHAK Phase 7 Potential Impact Assessments."""

    def __init__(self) -> None:
        self.method_registry = impact_method_registry
        self.claim_registry = claim_registry
        register_impact_claims(self.claim_registry)

    def evaluate_building(
        self,
        hazard: HazardEvaluation,
        building: BuildingFootprint,
        structural_class: Optional[BuildingStructuralClass] = None,
        vulnerability: Optional[VulnerabilityResult] = None,
        risk: Optional[RiskAssessment] = None,
        exposure_id: Optional[str] = None,
    ) -> PotentialImpactAssessment:
        """Evaluates physical structural damage for an exposed building."""
        self._validate_hazard(hazard)

        h_id = _get_hazard_id(hazard)
        h_type = _get_hazard_type_str(hazard)
        h_state = _get_hazard_state_str(hazard)
        q_state = _get_quality_state(hazard)

        vuln_score = vulnerability.score if vulnerability else None
        vuln_id = vulnerability.vulnerability_id if vulnerability else None
        risk_id = risk.risk_id if risk else None

        # Check for expired hazard
        now_dt = datetime.now(timezone.utc)
        if hazard.valid_to and hazard.valid_to < now_dt:
            assessment = evaluate_building_physical_damage(
                hazard_id=h_id,
                hazard_type=h_type,
                hazard_severity="NONE",
                building=building,
                structural_class=structural_class,
                vulnerability_score=vuln_score,
                exposure_id=exposure_id,
                vulnerability_id=vuln_id,
                risk_id=risk_id,
                quality_state=QualityState.STALE,
            )
            assessment.damage_state = DamageState.UNDETERMINED
            assessment.details["status_note"] = "Hazard validity expired; potential impact undetermined"
            return assessment

        # Handle stale hazard
        if q_state == QualityState.STALE:
            assessment = evaluate_building_physical_damage(
                hazard_id=h_id,
                hazard_type=h_type,
                hazard_severity="NONE",
                building=building,
                structural_class=structural_class,
                vulnerability_score=vuln_score,
                exposure_id=exposure_id,
                vulnerability_id=vuln_id,
                risk_id=risk_id,
                quality_state=QualityState.STALE,
            )
            assessment.damage_state = DamageState.UNDETERMINED
            assessment.damage_ratio = None
            assessment.details["status_note"] = "Rapidly evolving hazard observation is STALE; impact undetermined"
            return assessment

        assessment = evaluate_building_physical_damage(
            hazard_id=h_id,
            hazard_type=h_type,
            hazard_severity=h_state,
            building=building,
            structural_class=structural_class,
            vulnerability_score=vuln_score,
            exposure_id=exposure_id,
            vulnerability_id=vuln_id,
            risk_id=risk_id,
            quality_state=q_state,
        )
        return assessment

    def evaluate_road(
        self,
        hazard: HazardEvaluation,
        road: RoadSegment,
        observed_rainfall_mm: Optional[float] = None,
        inundation_depth_m: Optional[float] = None,
        vulnerability: Optional[VulnerabilityResult] = None,
        risk: Optional[RiskAssessment] = None,
        exposure_id: Optional[str] = None,
    ) -> PotentialImpactAssessment:
        """Evaluates transportation corridor disruption for an exposed road segment."""
        self._validate_hazard(hazard)

        h_id = _get_hazard_id(hazard)
        h_type = _get_hazard_type_str(hazard)
        h_state = _get_hazard_state_str(hazard)
        q_state = _get_quality_state(hazard)

        vuln_id = vulnerability.vulnerability_id if vulnerability else None
        risk_id = risk.risk_id if risk else None

        # Check for expired hazard
        now_dt = datetime.now(timezone.utc)
        if hazard.valid_to and hazard.valid_to < now_dt:
            assessment = evaluate_road_infrastructure_disruption(
                hazard_id=h_id,
                hazard_type=h_type,
                hazard_severity="NONE",
                road=road,
                observed_rainfall_mm=0.0,
                inundation_depth_m=0.0,
                exposure_id=exposure_id,
                vulnerability_id=vuln_id,
                risk_id=risk_id,
                quality_state=QualityState.STALE,
            )
            assessment.damage_state = DamageState.UNDETERMINED
            assessment.details["status_note"] = "Hazard validity expired; road disruption undetermined"
            return assessment

        if q_state == QualityState.STALE:
            assessment = evaluate_road_infrastructure_disruption(
                hazard_id=h_id,
                hazard_type=h_type,
                hazard_severity="NONE",
                road=road,
                observed_rainfall_mm=0.0,
                inundation_depth_m=0.0,
                exposure_id=exposure_id,
                vulnerability_id=vuln_id,
                risk_id=risk_id,
                quality_state=QualityState.STALE,
            )
            assessment.damage_state = DamageState.UNDETERMINED
            assessment.details["status_note"] = "Rapidly evolving hazard observation is STALE; road disruption undetermined"
            return assessment

        # If rainfall not explicitly passed, inspect hazard details
        rf = observed_rainfall_mm
        if rf is None:
            rf = getattr(hazard, "observed_value", None) or (hazard.details.get("rainfall_mm") if hasattr(hazard, "details") and hazard.details else None)

        assessment = evaluate_road_infrastructure_disruption(
            hazard_id=h_id,
            hazard_type=h_type,
            hazard_severity=h_state,
            road=road,
            observed_rainfall_mm=rf,
            inundation_depth_m=inundation_depth_m,
            exposure_id=exposure_id,
            vulnerability_id=vuln_id,
            risk_id=risk_id,
            quality_state=q_state,
        )
        return assessment

    def evaluate_hospital(
        self,
        hazard: HazardEvaluation,
        hospital: CriticalAsset,
        access_road_disrupted: bool = False,
        vulnerability: Optional[VulnerabilityResult] = None,
        risk: Optional[RiskAssessment] = None,
        exposure_id: Optional[str] = None,
    ) -> PotentialImpactAssessment:
        """Evaluates operational capacity at risk for an exposed healthcare facility."""
        self._validate_hazard(hazard)
        h_id = _get_hazard_id(hazard)
        h_type = _get_hazard_type_str(hazard)
        h_state = _get_hazard_state_str(hazard)
        q_state = _get_quality_state(hazard)

        return evaluate_hospital_service_disruption(
            hazard_id=h_id,
            hazard_type=h_type,
            hazard_severity=h_state,
            hospital=hospital,
            access_road_disrupted=access_road_disrupted,
            exposure_id=exposure_id,
            vulnerability_id=vulnerability.vulnerability_id if vulnerability else None,
            risk_id=risk.risk_id if risk else None,
            quality_state=q_state,
        )

    def evaluate_school(
        self,
        hazard: HazardEvaluation,
        school: CriticalAsset,
        vulnerability: Optional[VulnerabilityResult] = None,
        risk: Optional[RiskAssessment] = None,
        exposure_id: Optional[str] = None,
    ) -> PotentialImpactAssessment:
        """Evaluates operational disruption and shelter potential for an exposed school."""
        self._validate_hazard(hazard)
        h_id = _get_hazard_id(hazard)
        h_type = _get_hazard_type_str(hazard)
        h_state = _get_hazard_state_str(hazard)
        q_state = _get_quality_state(hazard)

        return evaluate_school_service_disruption(
            hazard_id=h_id,
            hazard_type=h_type,
            hazard_severity=h_state,
            school=school,
            exposure_id=exposure_id,
            vulnerability_id=vulnerability.vulnerability_id if vulnerability else None,
            risk_id=risk.risk_id if risk else None,
            quality_state=q_state,
        )

    def evaluate_agriculture(
        self,
        hazard: HazardEvaluation,
        crop_name: str,
        growth_stage: CropGrowthStage,
        planted_acres: float,
        baseline_yield_tonnes_per_acre: float = 1.5,
        vulnerability: Optional[VulnerabilityResult] = None,
        risk: Optional[RiskAssessment] = None,
        plot_id: Optional[str] = None,
        exposure_id: Optional[str] = None,
    ) -> PotentialImpactAssessment:
        """Evaluates phenological crop yield consequence and production deficit."""
        self._validate_hazard(hazard)
        h_id = _get_hazard_id(hazard)
        h_type = _get_hazard_type_str(hazard)
        h_state = _get_hazard_state_str(hazard)
        q_state = _get_quality_state(hazard)

        return evaluate_agricultural_yield_impact(
            hazard_id=h_id,
            hazard_type=h_type,
            hazard_severity=h_state,
            crop_name=crop_name,
            growth_stage=growth_stage,
            planted_acres=planted_acres,
            baseline_yield_tonnes_per_acre=baseline_yield_tonnes_per_acre,
            vulnerability_score=vulnerability.score if vulnerability else None,
            plot_id=plot_id,
            exposure_id=exposure_id,
            vulnerability_id=vulnerability.vulnerability_id if vulnerability else None,
            risk_id=risk.risk_id if risk else None,
            quality_state=q_state,
        )

    def evaluate_economic(
        self,
        hazard: HazardEvaluation,
        physical_impact: PotentialImpactAssessment,
        unit_cost_override: Optional[float] = None,
        valuation_source: Optional[str] = None,
    ) -> PotentialImpactAssessment:
        """Evaluates direct physical replacement/repair cost from an impact assessment."""
        self._validate_hazard(hazard)
        h_id = _get_hazard_id(hazard)
        q_state = _get_quality_state(hazard)

        return evaluate_direct_economic_loss(
            hazard_id=h_id,
            physical_impact=physical_impact,
            unit_cost_override=unit_cost_override,
            valuation_source=valuation_source,
            quality_state=q_state,
        )

    def evaluate_bundle(
        self,
        hazard: HazardEvaluation,
        assessments: List[PotentialImpactAssessment],
    ) -> ImpactEvaluationBundle:
        """Bundles multi-sector impact assessments for a hazard event into a unified evaluation."""
        self._validate_hazard(hazard)
        h_id = _get_hazard_id(hazard)

        bundle_id = f"BND-IMP-{h_id[:8]}-{uuid.uuid4().hex[:6]}"
        summary_by_type: Dict[str, int] = {}
        total_loss_inr = 0.0
        has_loss = False
        quality_warnings: List[str] = []

        for a in assessments:
            t_str = a.impact_type.value
            summary_by_type[t_str] = summary_by_type.get(t_str, 0) + 1
            if a.quality_state != QualityState.VALID:
                quality_warnings.append(f"Assessment {a.impact_id} has quality state {a.quality_state.value}")
            if a.economic_valuation and a.economic_valuation.estimated_loss is not None:
                total_loss_inr += a.economic_valuation.estimated_loss
                has_loss = True

        return ImpactEvaluationBundle(
            bundle_id=bundle_id,
            hazard_id=h_id,
            assessments=assessments,
            summary_by_type=summary_by_type,
            total_estimated_loss_inr=round(total_loss_inr, 2) if has_loss else None,
            has_quality_warning=bool(quality_warnings),
            quality_warnings=quality_warnings,
            summary_notes="Multi-sector potential impact bundle evaluated under VAYUBODHAK Phase 7 prototype rules",
        )

    def _validate_hazard(self, hazard: HazardEvaluation) -> None:
        """Validates hazard temporal and quality integrity."""
        q_state = _get_quality_state(hazard)
        h_id = _get_hazard_id(hazard)
        if q_state == QualityState.INVALID:
            raise ValueError(f"Hazard evaluation {h_id} has INVALID quality state.")

        now_dt = datetime.now(timezone.utc)
        if hazard.valid_from and hazard.valid_from > now_dt:
            raise ValueError(f"Hazard assessment {h_id} is future-dated (valid_from {hazard.valid_from} > current {now_dt}).")


# Global singleton instance
impact_engine = ImpactEngine()

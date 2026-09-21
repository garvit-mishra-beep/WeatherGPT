"""Deterministic risk models with decoupled orthogonal confidence and explicit exposure profiles."""

from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field
from app.brains.analyst_core.models.schemas import RiskLevel, ConfidenceLevel


class RiskFactor(BaseModel):
    """Individual contributing factor to risk assessment with explicit evidence links."""
    name: str
    component: str  # "hazard", "exposure", "vulnerability"
    score: float    # 0.0 to 100.0
    weight: float   # 0.0 to 1.0
    description: str
    evidence_ref: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)


class ExposureAssessment(BaseModel):
    """Evidence-based exposure assessment with model ID and methodology labeling."""
    status: str = "UNSPECIFIED"  # "ASSESSED", "UNSPECIFIED", "UNKNOWN"
    score: Optional[float] = None
    sector: Optional[str] = None
    population_density: Optional[str] = None
    rationale: str = "Exposure not specified by user or operational context."
    model_id: str = "EXP-MCDA-2024"
    model_version: str = "1.0"
    methodology: str = "Sectoral footprint & asset exposure scoring"
    assumption_status: str = "ASSUMED"  # "ASSESSED", "ASSUMED", "UNCONSTRAINED"


class VulnerabilityAssessment(BaseModel):
    """Evidence-based vulnerability assessment with model ID and methodology labeling."""
    status: str = "UNSPECIFIED"  # "ASSESSED", "UNSPECIFIED", "UNKNOWN"
    score: Optional[float] = None
    infrastructure_resilience: Optional[str] = None
    mitigation_measures_present: bool = False
    rationale: str = "Vulnerability not specified by user or operational context."
    model_id: str = "VULN-MCDA-2024"
    model_version: str = "1.0"
    methodology: str = "Structural & socioeconomic fragility index"
    assumption_status: str = "ASSUMED"  # "ASSESSED", "ASSUMED", "UNCONSTRAINED"


class RiskBreakdown(BaseModel):
    """Detailed decomposition of risk assessment inputs and weights."""
    hazard_severity: float = 0.0
    exposure: ExposureAssessment = Field(default_factory=ExposureAssessment)
    vulnerability: VulnerabilityAssessment = Field(default_factory=VulnerabilityAssessment)
    formula: str = "Composite: (hazard * W_h + exposure * W_e + vulnerability * W_v) when exposure/vuln assessed; otherwise Hazard-only."
    factors: List[RiskFactor] = Field(default_factory=list)
    explanation: str = ""

    @property
    def exposure_score(self) -> Optional[float]:
        return self.exposure.score

    @property
    def vulnerability_score(self) -> Optional[float]:
        return self.vulnerability.score


class RiskScore(BaseModel):
    """Explainable risk score with supporting factors, uncertainty intervals, and documented limitations."""
    score: Optional[float] = None
    level: RiskLevel
    breakdown: RiskBreakdown
    score_min: Optional[float] = None  # Uncertainty interval lower bound
    score_max: Optional[float] = None  # Uncertainty interval upper bound
    threshold_used: Optional[str] = None
    threshold_config_version: str = "IMD-MET-2024.1"
    risk_config_version: str = "RISK-WMO-2024.1"
    model_id: str = "RM-MCDA-2024"
    model_version: str = "1.0"
    methodology: str = "Multi-Criteria Decision Analysis (MCDA) Impact-Based Risk Model"
    assumption_status: str = "EVIDENCE_CONSTRAINED"
    limitations: List[str] = Field(default_factory=list)

    @classmethod
    def calculate(
        cls,
        hazard_severity: float,
        exposure: Optional[ExposureAssessment] = None,
        vulnerability: Optional[VulnerabilityAssessment] = None,
        confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM,
        uncertainty_spread: float = 10.0,
        factors: Optional[List[RiskFactor]] = None,
        has_sufficient_evidence: bool = True,
        threshold_used: Optional[str] = None,
        limitations: Optional[List[str]] = None,
        risk_config_version: str = "RISK-WMO-2024.1",
    ) -> "RiskScore":
        """Calculates risk score without conflating confidence into the risk magnitude."""
        from app.brains.analyst_core.models.risk_model_config import RiskModelRegistry
        risk_cfg = RiskModelRegistry.get_config(risk_config_version)

        exp = exposure or ExposureAssessment()
        vuln = vulnerability or VulnerabilityAssessment()

        if not has_sufficient_evidence or confidence_level == ConfidenceLevel.INSUFFICIENT_DATA:
            breakdown = RiskBreakdown(
                hazard_severity=hazard_severity,
                exposure=exp,
                vulnerability=vuln,
                factors=factors or [],
                explanation="Evidence is insufficient to reliably quantify risk.",
            )
            return cls(
                score=None,
                level=RiskLevel.UNKNOWN,
                breakdown=breakdown,
                score_min=None,
                score_max=None,
                threshold_used=threshold_used,
                risk_config_version=risk_cfg.config_version,
                model_id=risk_cfg.model_id,
                methodology=risk_cfg.methodology,
                assumption_status="INSUFFICIENT_EVIDENCE",
                limitations=limitations or ["Insufficient reliable meteorological evidence"],
            )

        hazard_clamped = max(0.0, min(100.0, hazard_severity))

        # Check if exposure and vulnerability are specified or unspecified
        if exp.status == "ASSESSED" and exp.score is not None and vuln.status == "ASSESSED" and vuln.score is not None:
            e_score = max(0.0, min(100.0, exp.score))
            v_score = max(0.0, min(100.0, vuln.score))
            final_score = round(
                (hazard_clamped * risk_cfg.hazard_weight_with_exposure)
                + (e_score * risk_cfg.exposure_weight)
                + (v_score * risk_cfg.vulnerability_weight),
                1
            )
            explanation = (
                f"Composite risk score: {final_score}/100 "
                f"(Hazard: {hazard_clamped:.1f} [w={risk_cfg.hazard_weight_with_exposure}], "
                f"Exposure: {e_score:.1f} [w={risk_cfg.exposure_weight}], "
                f"Vulnerability: {v_score:.1f} [w={risk_cfg.vulnerability_weight}])"
            )
            assumption_st = "EVIDENCE_CONSTRAINED"
        else:
            # Hazard-only risk potential (No arbitrary assumptions)
            final_score = round(hazard_clamped * risk_cfg.hazard_weight_unspecified, 1)
            explanation = (
                f"Hazard Risk Potential: {final_score}/100 "
                f"(Exposure and vulnerability were unspecified; score reflects raw meteorological hazard severity)"
            )
            assumption_st = "HAZARD_DOMINATED"

        # Compute uncertainty interval [min, max] based on confidence level
        interval_radii = {
            ConfidenceLevel.HIGH: max(4.0, uncertainty_spread * 0.5),
            ConfidenceLevel.MEDIUM: max(8.0, uncertainty_spread * 1.0),
            ConfidenceLevel.LOW: max(16.0, uncertainty_spread * 1.8),
            ConfidenceLevel.INSUFFICIENT_DATA: 35.0,
        }
        radius = interval_radii.get(confidence_level, 10.0)
        s_min = round(max(0.0, final_score - radius), 1)
        s_max = round(min(100.0, final_score + radius), 1)

        # Calibrated RiskLevel mapping based on physical thresholds
        if final_score < 20.0:
            level = RiskLevel.VERY_LOW
        elif final_score < 40.0:
            level = RiskLevel.LOW
        elif final_score < 65.0:
            level = RiskLevel.MODERATE
        elif final_score < 85.0:
            level = RiskLevel.HIGH
        else:
            level = RiskLevel.VERY_HIGH

        breakdown = RiskBreakdown(
            hazard_severity=hazard_clamped,
            exposure=exp,
            vulnerability=vuln,
            factors=factors or [],
            explanation=explanation,
        )

        return cls(
            score=final_score,
            level=level,
            breakdown=breakdown,
            score_min=s_min,
            score_max=s_max,
            threshold_used=threshold_used,
            risk_config_version=risk_cfg.config_version,
            model_id=risk_cfg.model_id,
            methodology=risk_cfg.methodology,
            assumption_status=assumption_st,
            limitations=limitations or [],
        )

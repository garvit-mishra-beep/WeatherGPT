"""Deterministic Quantitative Risk Engine for VAYUBODHAK Phase 6.

Combines Phase 3 HazardEvaluation, Phase 4 ExposureResult, and Phase 5 VulnerabilityResult
into deterministic, provenance-linked RiskAssessments.

CRITICAL INVARIANTS:
1. Reconciles Multiplicative (R = H * E * V) and Legacy Additive formulations.
2. Evaluates zero-boundary conditions: H=0, E=0, or V=0 yields zero risk in multiplicative mode.
3. Propagates Quality States (INVALID rejected, MISSING/CONFLICT undetermined, STALE flagged).
4. Preserves spatial resolution without unsupported downscaling.
5. Surfaces upstream historical dependencies (Census 2011) and prototype classifications.
6. Zero impact calculation: No damage, monetary loss, casualties, or evacuation orders.
"""

import hashlib
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.evidence.claim_gate import claim_gate
from app.evidence.models import QualityState, SourceAuthorityLevel
from app.exposure.models import (
    ExposureEvaluation,
    ExposureResult,
    ExposureType,
    SpatialResolution,
)
from app.hazard.models import HazardEvaluation, HazardState, HazardType
from app.risk.claims import register_risk_claims
from app.risk.method_registry import (
    RiskMethodRecord,
    RiskMethodRegistry,
    RiskMethodStatus,
    risk_method_registry,
)
from app.risk.models import (
    MethodClassification,
    RiskAssessment,
    RiskCategory,
    RiskComponentValues,
    RiskEvaluation,
    RiskScale,
    RiskUncertainty,
)
from app.vulnerability.models import VulnerabilityEvaluation, VulnerabilityResult


# Hierarchy for spatial resolution coarseness (lower index = finer, higher index = coarser)
SPATIAL_RESOLUTION_HIERARCHY: Dict[SpatialResolution, int] = {
    SpatialResolution.POINT: 1,
    SpatialResolution.BUILDING_FOOTPRINT: 2,
    SpatialResolution.ROAD_SEGMENT: 3,
    SpatialResolution.POPULATION_GRID_CELL: 4,
    SpatialResolution.FORECAST_GRID: 5,
    SpatialResolution.HAZARD_POLYGON: 6,
    SpatialResolution.ADMINISTRATIVE_POLYGON: 7,
}


class RiskEngine:
    """Canonical deterministic Quantitative Risk Engine."""

    def __init__(self, registry: RiskMethodRegistry = risk_method_registry) -> None:
        self.registry = registry
        register_risk_claims()

    # ------------------------------------------------------------------------
    # 1. Normalization Subroutines
    # ------------------------------------------------------------------------

    @staticmethod
    def normalize_hazard(hazard: HazardEvaluation) -> Tuple[float, str]:
        """Normalizes HazardEvaluation into dimensionless [0.0, 1.0] factor.
        
        Returns:
            Tuple of (normalized_hazard_score, hazard_state_name)
        """
        state = hazard.hazard_state

        if state == HazardState.NONE:
            return 0.0, state.value
        elif state == HazardState.WATCH:
            return 0.25, state.value
        elif state == HazardState.WARNING:
            return 0.50, state.value
        elif state == HazardState.SEVERE:
            return 0.75, state.value
        elif state == HazardState.EXTREME:
            return 1.00, state.value
        elif state == HazardState.UNDETERMINED:
            return 0.0, state.value
        else:
            return 0.0, str(state)

    @staticmethod
    def normalize_exposure(exposure: ExposureResult) -> float:
        """Normalizes raw exposure physical quantity into dimensionless [0.0, 1.0] factor.
        
        Applies governed logarithmic capacity scaling:
            E_norm = min(1.0, ln(1 + Q) / ln(1 + Q_ref))
        """
        q = float(exposure.quantity)
        if q <= 0.0:
            return 0.0

        # Reference capacities calibrated by exposure typology
        ref_capacities: Dict[ExposureType, float] = {
            ExposureType.POPULATION: 100_000.0,
            ExposureType.POPULATION_ADMIN: 100_000.0,
            ExposureType.POPULATION_GRIDDED: 10_000.0,
            ExposureType.BUILDING: 5_000.0,
            ExposureType.HOSPITAL: 50.0,
            ExposureType.SCHOOL: 100.0,
            ExposureType.POLICE_EMERGENCY: 50.0,
            ExposureType.CRITICAL_INFRASTRUCTURE: 50.0,
            ExposureType.ROAD: 100.0,          # 100 km
            ExposureType.AGRICULTURE: 10_000.0, # 10,000 acres
            ExposureType.ADMINISTRATIVE_ASSET: 50.0,
            ExposureType.OTHER_SUPPORTED_ASSET: 500.0,
        }

        q_ref = ref_capacities.get(exposure.exposure_type, 1_000.0)
        norm_e = math.log(1.0 + q) / math.log(1.0 + q_ref)
        return min(1.0, max(0.0, norm_e))

    @staticmethod
    def normalize_vulnerability(vulnerability: VulnerabilityResult) -> float:
        """Normalizes VulnerabilityResult into dimensionless [0.0, 1.0] factor."""
        if vulnerability.score is not None:
            return min(1.0, max(0.0, float(vulnerability.score)))

        # Fallback to category mapping if continuous score was unassigned
        category_map = {
            "LOW": 0.20,
            "MODERATE": 0.40,
            "HIGH": 0.70,
            "CRITICAL": 0.90,
            "UNDETERMINED": 0.50,
            "NOT_APPLICABLE": 0.0,
        }
        cat_str = vulnerability.category.value if hasattr(vulnerability.category, "value") else str(vulnerability.category)
        return category_map.get(cat_str, 0.50)

    # ------------------------------------------------------------------------
    # 2. Quality & Spatial/Temporal Lineage Helpers
    # ------------------------------------------------------------------------

    @staticmethod
    def resolve_quality_state(states: List[QualityState]) -> QualityState:
        """Resolves overall quality state across multiple input dependencies."""
        if any(s == QualityState.INVALID for s in states):
            return QualityState.INVALID
        if any(s == QualityState.CONFLICT for s in states):
            return QualityState.CONFLICT
        if any(s == QualityState.MISSING for s in states):
            return QualityState.MISSING
        if any(s == QualityState.STALE for s in states):
            return QualityState.STALE
        return QualityState.VALID

    @staticmethod
    def resolve_spatial_resolution(resolutions: List[SpatialResolution]) -> SpatialResolution:
        """Determines the inherited coarsest spatial resolution across components."""
        if not resolutions:
            return SpatialResolution.ADMINISTRATIVE_POLYGON
        return max(resolutions, key=lambda r: SPATIAL_RESOLUTION_HIERARCHY.get(r, 7))

    @staticmethod
    def compute_provenance_hash(
        hazard_id: str,
        exposure_id: str,
        vulnerability_id: str,
        method_id: str,
        method_version: str,
        score: Optional[float],
        category: RiskCategory,
    ) -> str:
        """Generates a cryptographic SHA-256 digest uniquely identifying the evaluation."""
        payload = (
            f"{hazard_id}:{exposure_id}:{vulnerability_id}:"
            f"{method_id}:{method_version}:{score}:{category.value}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------------
    # 3. Categorization
    # ------------------------------------------------------------------------

    @staticmethod
    def categorize_risk(score: Optional[float], method: RiskMethodRecord) -> RiskCategory:
        """Categorizes a numeric risk score according to registered method thresholds."""
        if score is None:
            return RiskCategory.UNDETERMINED

        if method.scale == RiskScale.INDEX_0_TO_1:
            # Thresholds: LOW < 0.05, MODERATE < 0.20, HIGH < 0.50, else CRITICAL
            low_t = method.thresholds.get("LOW", 0.05)
            mod_t = method.thresholds.get("MODERATE", 0.20)
            high_t = method.thresholds.get("HIGH", 0.50)

            if score < low_t:
                return RiskCategory.LOW
            elif score < mod_t:
                return RiskCategory.MODERATE
            elif score < high_t:
                return RiskCategory.HIGH
            else:
                return RiskCategory.CRITICAL

        elif method.scale == RiskScale.INDEX_0_TO_10:
            # Legacy thresholds: LOW < 3.5, MODERATE < 7.0, else HIGH/CRITICAL
            low_t = method.thresholds.get("LOW", 3.5)
            mod_t = method.thresholds.get("MODERATE", 7.0)

            if score < low_t:
                return RiskCategory.LOW
            elif score < mod_t:
                return RiskCategory.MODERATE
            else:
                return RiskCategory.HIGH

        return RiskCategory.UNDETERMINED

    # ------------------------------------------------------------------------
    # 4. Primary Risk Evaluation Engine
    # ------------------------------------------------------------------------

    def evaluate_risk(
        self,
        hazard: HazardEvaluation,
        exposure: ExposureResult,
        vulnerability: VulnerabilityResult,
        method_id: str = "RISK-METH-MULT-001",
        claim_id: Optional[str] = "CLM-RISK-ASSESSMENT-001",
    ) -> RiskAssessment:
        """Evaluates deterministic risk for a specific (Hazard, Exposure, Vulnerability) triad."""
        method = self.registry.get_method(method_id)
        if not method:
            raise ValueError(f"Risk method '{method_id}' is not registered in RiskMethodRegistry")

        if method.status != RiskMethodStatus.ACTIVE:
            raise ValueError(
                f"Cannot evaluate with risk method '{method_id}' because its status is '{method.status.value}'. "
                "Only ACTIVE methods may execute in production."
            )

        # 1. Quality State Gating
        quality_states = [
            hazard.quality_state if isinstance(hazard.quality_state, QualityState) else QualityState(hazard.quality_state),
            exposure.quality_state,
            vulnerability.quality_state,
        ]
        overall_quality = self.resolve_quality_state(quality_states)

        if overall_quality == QualityState.INVALID:
            raise ValueError(
                f"Risk assessment blocked: One or more upstream inputs has INVALID quality state: "
                f"Hazard={hazard.quality_state}, Exposure={exposure.quality_state}, Vulnerability={vulnerability.quality_state}"
            )

        # 2. Temporal & Historical Handling
        now_utc = datetime.now(timezone.utc)
        hazard_valid_from = hazard.valid_from.replace(tzinfo=timezone.utc) if hazard.valid_from and hazard.valid_from.tzinfo is None else hazard.valid_from
        hazard_valid_to = hazard.valid_to.replace(tzinfo=timezone.utc) if hazard.valid_to and hazard.valid_to.tzinfo is None else hazard.valid_to

        if hazard_valid_from and hazard_valid_from > now_utc:
            raise ValueError(f"Future-dated hazard evaluation rejected: valid_from {hazard_valid_from} is in the future")

        is_expired = False
        if hazard_valid_to and hazard_valid_to < now_utc:
            is_expired = True

        # Check historical baseline propagation from vulnerability or exposure
        is_historical = (
            getattr(vulnerability.uncertainty, "is_historical", False)
            or getattr(exposure.uncertainty, "is_estimate", False)
        )
        hist_ref_year = getattr(vulnerability.uncertainty, "historical_reference_year", None)

        # 3. Spatial Resolution Inheritance
        inherited_spatial_resolution = self.resolve_spatial_resolution([
            exposure.spatial_resolution,
            vulnerability.spatial_resolution,
        ])

        # 4. Normalization of Components
        h_norm, h_state_name = self.normalize_hazard(hazard)
        e_norm = self.normalize_exposure(exposure)
        v_norm = self.normalize_vulnerability(vulnerability)

        components = RiskComponentValues(
            hazard_raw=hazard.observed_value,
            hazard_unit=hazard.observed_unit,
            hazard_state=h_state_name,
            hazard_normalized=round(h_norm, 4),
            exposure_raw=round(float(exposure.quantity), 2),
            exposure_unit=exposure.unit,
            exposure_normalized=round(e_norm, 4),
            vulnerability_raw=vulnerability.score,
            vulnerability_category=vulnerability.category.value if hasattr(vulnerability.category, "value") else str(vulnerability.category),
            vulnerability_normalized=round(v_norm, 4),
        )

        # 5. Calculation based on selected governed method
        score: Optional[float] = None
        category: RiskCategory = RiskCategory.UNDETERMINED

        # Stale Data Policy:
        # 1. Stale Hazard: Rapidly evolving atmospheric hazard observations that are stale
        #    cannot reliably quantify real-time risk. Output is gated as UNDETERMINED.
        # 2. Stale Exposure / Vulnerability: Permitted if the method supports static/historical baselines,
        #    retaining QualityState.STALE and setting data quality warnings.
        hazard_quality = hazard.quality_state if isinstance(hazard.quality_state, QualityState) else QualityState(hazard.quality_state)
        is_hazard_stale = (hazard_quality == QualityState.STALE)

        if (
            overall_quality in (QualityState.MISSING, QualityState.CONFLICT)
            or hazard.hazard_state == HazardState.UNDETERMINED
            or is_expired
            or is_hazard_stale
        ):
            score = None
            category = RiskCategory.UNDETERMINED
        else:
            if method.method_id == "RISK-METH-MULT-001":
                # Strict Multiplicative: R = H * E * V in [0.0, 1.0]
                calculated_score = h_norm * e_norm * v_norm
                score = round(min(1.0, max(0.0, calculated_score)), 4)
                category = self.categorize_risk(score, method)

            elif method.method_id == "RISK-METH-ADD-001":
                # Legacy Additive: R = 0.50 * H_10 + 0.30 * E_10 + 0.20 * V_10 in [0.0, 10.0]
                h_10 = h_norm * 10.0
                e_10 = e_norm * 10.0
                v_10 = v_norm * 10.0
                calculated_score = (0.50 * h_10) + (0.30 * e_10) + (0.20 * v_10)
                score = round(min(10.0, max(0.0, calculated_score)), 2)
                category = self.categorize_risk(score, method)

            else:
                raise NotImplementedError(f"Computation for method '{method.method_id}' is not implemented")

        # 6. Prototype Status Propagation
        upstream_prototype = (
            vulnerability.is_prototype
            or vulnerability.method_classification == MethodClassification.VAYUBODHAK_PROTOTYPE
        )

        # 7. Uncertainty and Limitations Construction
        limitations = list(method.limitations)
        if is_hazard_stale:
            limitations.append("Stale meteorological hazard observation cannot reliably quantify real-time risk; evaluation undetermined")
        if is_expired:
            limitations.append("Hazard validity window expired prior to risk assessment")
        if is_historical:
            limitations.append(f"Demographic or baseline data relies on historical census ({hist_ref_year or 2011})")
        if upstream_prototype:
            limitations.append("Vulnerability input was derived using a VAYUBODHAK prototype method")

        uncertainty = RiskUncertainty(
            methodology=method.description,
            spatial_resolution=inherited_spatial_resolution,
            assumptions=[
                "Spatial concordance of hazard footprint, exposed assets, and vulnerability boundary",
                "Monotonic relationship between normalized exposure/vulnerability and disaster risk",
                "Capacity (coping/adaptive capacity) is outside the scope of this numerical calculation",
            ],
            limitations=limitations,
            is_historical=is_historical,
            historical_reference_year=hist_ref_year,
            prototype_dependency=upstream_prototype,
            method_classification=method.classification,
            source_basis_disclosure=(
                f"Calculated via {method.method_name} ({method.citation}). "
                "Passing automated software tests verifies implementation correctness only; "
                "it does not independently validate empirical real-world risk fidelity."
            ),
            capacity_represented=False,
            capacity_boundary_disclosure=(
                "Capacity (coping/adaptive capacity) is part of broader disaster risk concepts (e.g. UNDRR), "
                "but is not represented in the current VAYUBODHAK numerical risk index. "
                "Deferred to later resilience and decision phases."
            ),
        )

        # 8. Deterministic ID and Provenance Digest
        risk_hash_base = (
            f"{hazard.hazard_id}:{exposure.exposure_id}:{vulnerability.vulnerability_id}:"
            f"{method.method_id}:{score}:{category.value}"
        )
        risk_id = f"RSK-{hashlib.sha256(risk_hash_base.encode('utf-8')).hexdigest()[:12]}"
        provenance_id = self.compute_provenance_hash(
            hazard_id=hazard.hazard_id,
            exposure_id=exposure.exposure_id,
            vulnerability_id=vulnerability.vulnerability_id,
            method_id=method.method_id,
            method_version=method.version,
            score=score,
            category=category,
        )

        # 9. Lineage and Evidence Aggregation
        all_evidence_ids = sorted(list(set(
            hazard.evidence_ids + exposure.evidence_ids + vulnerability.evidence_ids
        )))
        derived_from = [hazard.hazard_id, exposure.exposure_id, vulnerability.vulnerability_id]

        # 10. Construct Canonical Assessment
        assessment = RiskAssessment(
            risk_id=risk_id,
            hazard_id=hazard.hazard_id,
            exposure_id=exposure.exposure_id,
            vulnerability_id=vulnerability.vulnerability_id,
            hazard_type=hazard.hazard_type.value if hasattr(hazard.hazard_type, "value") else str(hazard.hazard_type),
            entity_type=exposure.exposure_type.value if hasattr(exposure.exposure_type, "value") else str(exposure.exposure_type),
            entity_id=vulnerability.entity_id or exposure.location.get("admin_code") if exposure.location else None,
            location=exposure.location or hazard.location,
            score=score,
            scale=method.scale,
            category=category,
            components=components,
            method_id=method.method_id,
            method_version=method.version,
            method_classification=method.classification,
            is_prototype=method.is_prototype,
            prototype_dependency=upstream_prototype,
            source_authority_level=vulnerability.source_authority_level,
            assessment_time=now_utc,
            valid_from=hazard.valid_from,
            valid_to=hazard.valid_to,
            spatial_resolution=inherited_spatial_resolution,
            quality_state=overall_quality,
            uncertainty=uncertainty,
            evidence_ids=all_evidence_ids,
            provenance_id=provenance_id,
            derived_from=derived_from,
            claim_id=claim_id,
            details={
                "hazard_state": h_state_name,
                "exposure_unit": exposure.unit,
                "exposure_raw": exposure.quantity,
                "vulnerability_category": components.vulnerability_category,
            },
        )

        return assessment

    # ------------------------------------------------------------------------
    # 5. Multi-Input Bundle Evaluation
    # ------------------------------------------------------------------------

    def evaluate_bundle(
        self,
        hazard: HazardEvaluation,
        exposure_bundle: ExposureEvaluation,
        vulnerability_bundle: VulnerabilityEvaluation,
        method_id: str = "RISK-METH-MULT-001",
    ) -> RiskEvaluation:
        """Evaluates risk across matching pairs in exposure and vulnerability bundles.
        
        Preserves individual entity assessments without arbitrary multi-hazard summation.
        """
        now_utc = datetime.now(timezone.utc)
        eval_id = f"RSK-EVAL-{hashlib.sha256(f'{hazard.hazard_id}:{exposure_bundle.evaluation_id}:{vulnerability_bundle.evaluation_id}'.encode('utf-8')).hexdigest()[:12]}"
        
        assessments: List[RiskAssessment] = []
        summary_categories: Dict[str, str] = {}
        quality_warnings: List[str] = []

        # Index vulnerability results by entity_type or exposure_id
        vuln_by_exposure_id: Dict[str, VulnerabilityResult] = {}
        vuln_by_entity_type: Dict[str, VulnerabilityResult] = {}
        for vr in vulnerability_bundle.vulnerability_results:
            if vr.exposure_id:
                vuln_by_exposure_id[vr.exposure_id] = vr
            vuln_by_entity_type[vr.entity_type] = vr

        for exp_res in exposure_bundle.exposure_results:
            # Find matching vulnerability record
            target_vuln = vuln_by_exposure_id.get(exp_res.exposure_id)
            if not target_vuln:
                target_vuln = vuln_by_entity_type.get(exp_res.exposure_type.value)

            if target_vuln:
                try:
                    assessment = self.evaluate_risk(
                        hazard=hazard,
                        exposure=exp_res,
                        vulnerability=target_vuln,
                        method_id=method_id,
                    )
                    assessments.append(assessment)
                    summary_categories[exp_res.exposure_type.value] = assessment.category.value
                    if assessment.quality_state == QualityState.STALE:
                        quality_warnings.append(f"Stale dependency in assessment for {exp_res.exposure_type.value}")
                except Exception as exc:
                    quality_warnings.append(f"Evaluation failed for {exp_res.exposure_type.value}: {str(exc)}")

        has_warning = len(quality_warnings) > 0 or any(a.quality_state == QualityState.STALE for a in assessments)

        return RiskEvaluation(
            evaluation_id=eval_id,
            hazard_evaluation_id=hazard.hazard_id,
            evaluated_at=now_utc,
            risk_assessments=assessments,
            summary_categories=summary_categories,
            has_data_quality_warning=has_warning,
            quality_warnings=quality_warnings,
        )


# Global singleton instance
risk_engine = RiskEngine()

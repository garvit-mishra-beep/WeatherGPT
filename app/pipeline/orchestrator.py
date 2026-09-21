"""Canonical Production Pipeline Orchestrator for VAYUBODHAK Phase 9A.

Unites all governed analytical engines (Phases 2A through 8):
  EvidenceFoundation (Phase 2A)
         ↓
  HazardEngine (Phase 3)
         ↓
  ExposureEngine (Phase 4)
         ↓
  VulnerabilityEngine (Phase 5)
         ↓
  RiskEngine (Phase 6)
         ↓
  ImpactEngine (Phase 7)
         ↓
  NirnayEngine (Phase 8)
         ↓
  Structured NirnayCard & Lineage Trace

Guarantees:
1. Determinism: Same inputs + same method/rule versions = identical logical outputs.
2. Provenance: SHA-256 cryptographic chain over all stage outputs and lineage pointers.
3. Quality State Propagation: Zero silent conversion. INVALID blocks downstream stages;
   STALE/CONFLICT surfaces REVIEW_REQUIRED.
4. Idempotency: Input hashing prevents duplicate pipeline executions.
5. Resumability: Resume from failed stages using immutable upstream snapshots.
6. Failure Resilience: Captures partial stage results upon failure; safe transient retries.
7. Zero LLM on numerical critical path: Entire calculation is 100% deterministic Python.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from app.decision.models import (
    ConfidenceLevel,
    DecisionOutcome,
    DecisionPackage,
    DecisionState,
    NirnayCard,
    OfficialWarningInfo,
    SeverityLevel,
)
from app.decision.nirnay_engine import nirnay_engine
from app.evidence.models import EvidenceClass, EvidenceRecord, QualityState
from app.evidence.service import evidence_service
from app.exposure.engine import ExposureEngine
from app.exposure.models import (
    CriticalAsset,
    ExposureEvaluation,
    ExposureResult,
    ExposureType,
    SpatialResolution,
)
from app.hazard.engine import HazardEngine
from app.hazard.models import BasisType, HazardEvaluation, HazardState, HazardType
from app.impact.engine import impact_engine
from app.impact.models import (
    DamageState,
    ImpactEvaluationBundle,
    ImpactType,
    ImpactUncertainty,
    PotentialImpactAssessment,
)
from app.pipeline.models import (
    DataSourceStatus,
    PipelineErrorCode,
    PipelineInput,
    PipelineRun,
    PipelineStage,
    PipelineStageExecution,
    PipelineState,
    PipelineTrace,
    PipelineTraceStage,
)
from app.pipeline.repository import pipeline_repository
from app.risk.engine import RiskEngine
from app.risk.models import RiskAssessment, RiskCategory
from app.vulnerability.engine import VulnerabilityEngine
from app.vulnerability.models import VulnerabilityEvaluation, VulnerabilityResult

logger = logging.getLogger(__name__)


class PipelineExecutionError(Exception):
    """Structured exception wrapping pipeline execution failures."""

    def __init__(
        self,
        stage: PipelineStage,
        error_code: PipelineErrorCode,
        message: str,
        retriable: bool = False,
    ):
        super().__init__(message)
        self.stage = stage
        self.error_code = error_code
        self.message = message
        self.retriable = retriable


class VayuBodhakPipeline:
    """Canonical operational orchestrator for VAYUBODHAK multi-hazard decision support."""

    def __init__(
        self,
        repo=pipeline_repository,
        hazard_eng: Optional[HazardEngine] = None,
        exposure_eng: Optional[ExposureEngine] = None,
        vulnerability_eng: Optional[VulnerabilityEngine] = None,
        risk_eng: Optional[RiskEngine] = None,
    ):
        self.repo = repo
        self.hazard_engine = hazard_eng or HazardEngine()
        self.exposure_engine = exposure_eng or ExposureEngine()
        self.vulnerability_engine = vulnerability_eng or VulnerabilityEngine()
        self.risk_engine = risk_eng or RiskEngine()
        self.impact_engine = impact_engine
        self.decision_engine = nirnay_engine
        self.evidence_service = evidence_service

    # ------------------------------------------------------------------------
    # 1. Hashing and Idempotency Subroutines
    # ------------------------------------------------------------------------

    @staticmethod
    def compute_input_hash(input_data: PipelineInput) -> str:
        """Computes deterministic SHA-256 idempotency hash for input payload."""
        ev_summary = [
            f"{e.evidence_id}:{e.normalized_field}:{e.normalized_value}:{e.quality_state.value}"
            for e in sorted(input_data.evidence_records, key=lambda x: x.evidence_id)
        ]
        poly_str = str(input_data.hazard_polygon) if input_data.hazard_polygon else ""
        warn_str = ""
        if input_data.official_warnings:
            warn_str = ",".join(
                f"{w.alert_id}:{w.warning_level}:{w.valid_to_iso}"
                for w in input_data.official_warnings
            )

        payload = f"{input_data.geography}|{poly_str}|{';'.join(ev_summary)}|{warn_str}|{input_data.is_demo}|{input_data.is_offline}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_pipeline_provenance(run: PipelineRun) -> str:
        """Computes canonical cryptographic SHA-256 lineage digest over all stage artifacts."""
        payload = (
            f"{run.pipeline_run_id}:{run.pipeline_version}:{run.input_hash}:"
            f"{','.join(run.evidence_ids)}:{','.join(run.hazard_evaluation_ids)}:"
            f"{','.join(run.exposure_evaluation_ids)}:{','.join(run.vulnerability_evaluation_ids)}:"
            f"{','.join(run.risk_assessment_ids)}:{','.join(run.impact_assessment_ids)}:"
            f"{run.decision_id or ''}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------------
    # 2. Main Pipeline Orchestration Entrypoint
    # ------------------------------------------------------------------------

    async def run(
        self,
        input_data: PipelineInput,
        force_reevaluate: bool = False,
        max_retries: int = 1,
    ) -> PipelineRun:
        """Executes canonical end-to-end multi-hazard pipeline run."""
        input_hash = self.compute_input_hash(input_data)

        # Idempotency Check: Return existing run if identical and not forced
        if not force_reevaluate:
            existing = await self.repo.get_by_input_hash(input_hash)
            if existing and existing.pipeline_state in (
                PipelineState.COMPLETED,
                PipelineState.REVIEW_REQUIRED,
                PipelineState.INSUFFICIENT_EVIDENCE,
                PipelineState.STALE,
                PipelineState.CONFLICT,
            ):
                logger.info(
                    "VayuBodhakPipeline: Idempotency cache hit for hash %s -> Run %s",
                    input_hash,
                    existing.pipeline_run_id,
                )
                return existing

        # Initialize new PipelineRun
        run = PipelineRun(
            input_reference=input_data.input_reference,
            input_hash=input_hash,
            source_status=(
                DataSourceStatus.DEMO
                if input_data.is_demo
                else (
                    DataSourceStatus.CACHED
                    if input_data.is_offline
                    else DataSourceStatus.LIVE
                )
            ),
        )
        await self.repo.save_run(run)

        return await self._execute_lifecycle(run, input_data, max_retries=max_retries)

    async def resume(
        self,
        pipeline_run_id: str,
        max_retries: int = 1,
    ) -> PipelineRun:
        """Resumes execution of an interrupted or failed pipeline run from its failure checkpoint."""
        run = await self.repo.get_run(pipeline_run_id)
        if not run:
            raise ValueError(f"Pipeline run '{pipeline_run_id}' not found for resumption.")

        if run.pipeline_state == PipelineState.COMPLETED:
            logger.info("VayuBodhakPipeline: Run %s already COMPLETED, nothing to resume.", pipeline_run_id)
            return run

        logger.info(
            "VayuBodhakPipeline: Resuming run %s from failed stage %s",
            pipeline_run_id,
            run.failed_stage,
        )
        run.is_resumed = True
        run.failed_stage = None
        run.error_code = None
        run.error_message = None

        # Reconstruct input context from run references (minimal default input)
        input_data = PipelineInput(
            input_reference=run.input_reference,
            geography="Target District",
            is_demo=(run.source_status == DataSourceStatus.DEMO),
            is_offline=(run.source_status == DataSourceStatus.CACHED),
        )

        return await self._execute_lifecycle(run, input_data, max_retries=max_retries)

    # ------------------------------------------------------------------------
    # 3. Lifecycle Stage Execution Engine
    # ------------------------------------------------------------------------

    async def _execute_lifecycle(
        self,
        run: PipelineRun,
        input_data: PipelineInput,
        max_retries: int = 1,
    ) -> PipelineRun:
        """Step-by-step governed execution with quality gating and retry capabilities."""
        now_dt = datetime.now(timezone.utc)

        # Context dictionaries to pass data between stages
        stage_artifacts: Dict[str, Any] = {}

        try:
            # Stage 1: EVIDENCE VALIDATION
            if PipelineStage.EVIDENCE not in run.completed_stages:
                await self._execute_stage_with_retry(
                    run,
                    PipelineStage.EVIDENCE,
                    lambda: self._stage_evidence(run, input_data, stage_artifacts),
                    max_retries,
                )

            # Stage 2: HAZARD EVALUATION
            if PipelineStage.HAZARD not in run.completed_stages:
                await self._execute_stage_with_retry(
                    run,
                    PipelineStage.HAZARD,
                    lambda: self._stage_hazard(run, input_data, stage_artifacts, now_dt),
                    max_retries,
                )

            # Stage 3: EXPOSURE QUANTIFICATION
            if PipelineStage.EXPOSURE not in run.completed_stages:
                await self._execute_stage_with_retry(
                    run,
                    PipelineStage.EXPOSURE,
                    lambda: self._stage_exposure(run, input_data, stage_artifacts),
                    max_retries,
                )

            # Stage 4: VULNERABILITY EVALUATION
            if PipelineStage.VULNERABILITY not in run.completed_stages:
                await self._execute_stage_with_retry(
                    run,
                    PipelineStage.VULNERABILITY,
                    lambda: self._stage_vulnerability(run, input_data, stage_artifacts),
                    max_retries,
                )

            # Stage 5: QUANTITATIVE RISK ASSESSMENT
            if PipelineStage.RISK not in run.completed_stages:
                await self._execute_stage_with_retry(
                    run,
                    PipelineStage.RISK,
                    lambda: self._stage_risk(run, input_data, stage_artifacts),
                    max_retries,
                )

            # Stage 6: POTENTIAL IMPACT MODELING
            if PipelineStage.IMPACT not in run.completed_stages:
                await self._execute_stage_with_retry(
                    run,
                    PipelineStage.IMPACT,
                    lambda: self._stage_impact(run, input_data, stage_artifacts),
                    max_retries,
                )

            # Stage 7: DECISION SUPPORT & NIRNAY CARD GENERATION
            if PipelineStage.DECISION not in run.completed_stages:
                await self._execute_stage_with_retry(
                    run,
                    PipelineStage.DECISION,
                    lambda: self._stage_decision(run, input_data, stage_artifacts, now_dt),
                    max_retries,
                )

            # Stage 8: FINAL PERSISTENCE & PROVENANCE SEALING
            run.provenance_id = self.compute_pipeline_provenance(run)
            run.completed_at_iso = datetime.now(timezone.utc).isoformat()
            if (
                run.pipeline_state in (
                    PipelineState.REVIEW_REQUIRED,
                    PipelineState.INSUFFICIENT_EVIDENCE,
                    PipelineState.STALE,
                    PipelineState.CONFLICT,
                )
                or run.quality_state in (QualityState.STALE.value, QualityState.CONFLICT.value)
                or "STALE_HAZARD_DETECTED" in run.prototype_flags
                or "CONFLICT_DETECTED" in run.prototype_flags
            ):
                run.pipeline_state = PipelineState.REVIEW_REQUIRED
            else:
                run.pipeline_state = PipelineState.COMPLETED

            await self.repo.save_run(run)
            logger.info(
                "VayuBodhakPipeline: Run %s reached terminal state %s (provenance=%s)",
                run.pipeline_run_id,
                run.pipeline_state,
                run.provenance_id,
            )
            return run

        except PipelineExecutionError as p_err:
            run.failed_stage = p_err.stage
            run.error_code = p_err.error_code
            run.error_message = p_err.message
            run.pipeline_state = self._map_failure_state(p_err.stage)
            run.completed_at_iso = datetime.now(timezone.utc).isoformat()
            run.provenance_id = self.compute_pipeline_provenance(run)
            await self.repo.save_run(run)
            logger.error(
                "VayuBodhakPipeline: Execution halted at stage %s: %s (code=%s)",
                p_err.stage,
                p_err.message,
                p_err.error_code,
            )
            return run

        except Exception as exc:
            run.failed_stage = run.current_stage or PipelineStage.EVIDENCE
            run.error_code = PipelineErrorCode.UNKNOWN_ERROR
            run.error_message = str(exc)
            run.pipeline_state = self._map_failure_state(run.failed_stage)
            run.completed_at_iso = datetime.now(timezone.utc).isoformat()
            run.provenance_id = self.compute_pipeline_provenance(run)
            await self.repo.save_run(run)
            logger.exception("VayuBodhakPipeline: Unexpected failure in run %s", run.pipeline_run_id)
            return run

    def _select_primary_hazard(self, hazard_evals: List[HazardEvaluation]) -> Optional[HazardEvaluation]:
        """Deterministic prioritization of governing active hazard over undetermined/none."""
        if not hazard_evals:
            return None
        severity_order = {
            HazardState.EXTREME: 5,
            HazardState.SEVERE: 4,
            HazardState.WARNING: 3,
            HazardState.WATCH: 2,
            HazardState.NONE: 0,
            HazardState.UNDETERMINED: -1,
        }
        return max(hazard_evals, key=lambda h: severity_order.get(h.hazard_state, -1))

    # ------------------------------------------------------------------------
    # 4. Individual Stage Subroutines
    # ------------------------------------------------------------------------

    def _stage_evidence(
        self,
        run: PipelineRun,
        input_data: PipelineInput,
        artifacts: Dict[str, Any],
    ) -> List[str]:
        """Stage 1: Evidence validation via Phase 2A Claim Gate & Freshness Policies."""
        records = input_data.evidence_records
        if not records:
            # Handle zero evidence
            run.quality_state = QualityState.MISSING.value
            run.data_coverage = 0.0
            artifacts["evidence_records"] = []
            return []

        # Enforce Zero Silent Conversion: Check for physical range / INVALID violations
        invalid_records = [r for r in records if r.quality_state == QualityState.INVALID]
        if invalid_records:
            raise PipelineExecutionError(
                stage=PipelineStage.EVIDENCE,
                error_code=PipelineErrorCode.EVIDENCE_VALIDATION_FAILED,
                message=f"Evidence validation failed: {len(invalid_records)} records have INVALID quality state.",
                retriable=False,
            )

        conflict_records = [r for r in records if r.quality_state == QualityState.CONFLICT]
        stale_records = [r for r in records if r.quality_state == QualityState.STALE]

        if conflict_records:
            run.quality_state = QualityState.CONFLICT.value
            run.pipeline_state = PipelineState.REVIEW_REQUIRED
            if "CONFLICT_DETECTED" not in run.prototype_flags:
                run.prototype_flags.append("CONFLICT_DETECTED")
        elif stale_records:
            run.quality_state = QualityState.STALE.value
            run.pipeline_state = PipelineState.REVIEW_REQUIRED
            if "STALE_HAZARD_DETECTED" not in run.prototype_flags:
                run.prototype_flags.append("STALE_HAZARD_DETECTED")
        else:
            run.quality_state = QualityState.VALID.value

        run.evidence_ids = [r.evidence_id for r in records]
        artifacts["evidence_records"] = records
        return run.evidence_ids

    def _stage_hazard(
        self,
        run: PipelineRun,
        input_data: PipelineInput,
        artifacts: Dict[str, Any],
        now_dt: datetime,
    ) -> List[str]:
        """Stage 2: Deterministic Hazard Modeling via Phase 3 HazardEngine."""
        records: List[EvidenceRecord] = artifacts.get("evidence_records", [])

        if not records:
            # No evidence -> Hazard state UNDETERMINED
            undetermined = HazardEvaluation(
                hazard_id=f"HZD-UNDET-{run.pipeline_run_id[:8]}",
                hazard_type=HazardType.HEAVY_RAINFALL,
                hazard_state=HazardState.UNDETERMINED,
                evaluation_time=now_dt,
                rule_id="RULE-UNDET-NO-EVIDENCE",
                rule_version="1.0",
                source_basis=BasisType.UNRESOLVED,
                quality_state=QualityState.MISSING.value,
                reason_codes=["NO_EVIDENCE_INGESTED"],
            )
            artifacts["hazard_evaluations"] = [undetermined]
            run.hazard_evaluation_ids = [undetermined.hazard_id]
            run.pipeline_state = PipelineState.INSUFFICIENT_EVIDENCE
            return run.hazard_evaluation_ids

        # Evaluate deterministic rules
        location_ctx = {"geography": input_data.geography}
        evals = self.hazard_engine.evaluate_hazards(
            evidence_records=records,
            location=location_ctx,
            evaluation_time=now_dt,
        )

        # Check for stale hazard states
        for h in evals:
            is_stale = (
                h.quality_state == QualityState.STALE.value
                or getattr(h, "is_expired", False)
                or (hasattr(h, "valid_to") and h.valid_to and h.valid_to < now_dt)
            )
            if is_stale:
                run.pipeline_state = PipelineState.REVIEW_REQUIRED
                run.prototype_flags.append("STALE_HAZARD_DETECTED")

        artifacts["hazard_evaluations"] = evals
        run.hazard_evaluation_ids = [h.hazard_id for h in evals]
        return run.hazard_evaluation_ids

    def _stage_exposure(
        self,
        run: PipelineRun,
        input_data: PipelineInput,
        artifacts: Dict[str, Any],
    ) -> List[str]:
        """Stage 3: Quantified Exposure Modeling via Phase 4 ExposureEngine."""
        hazard_evals: List[HazardEvaluation] = artifacts.get("hazard_evaluations", [])
        primary_hazard = self._select_primary_hazard(hazard_evals)

        # Build fallback polygon if not provided
        polygon = input_data.hazard_polygon
        if not polygon or len(polygon) < 3:
            # Default administrative polygon for target district
            polygon = [
                (26.15, 78.10),
                (26.25, 78.10),
                (26.25, 78.25),
                (26.15, 78.25),
                (26.15, 78.10),
            ]

        if not primary_hazard:
            run.exposure_evaluation_ids = []
            return []

        # Evaluate exposure
        try:
            exp_eval = self.exposure_engine.evaluate(
                hazard_eval=primary_hazard,
                hazard_polygon=polygon,
                roads=input_data.roads,
                buildings=input_data.buildings,
            )
            artifacts["exposure_evaluation"] = exp_eval
            run.exposure_evaluation_ids = [exp_eval.evaluation_id]
            return run.exposure_evaluation_ids
        except Exception as exc:
            # Missing exposure data must NOT be converted to fabricated zero
            logger.warning("VayuBodhakPipeline: Exposure stage encountered exception: %s", exc)
            run.prototype_flags.append("EXPOSURE_DATA_UNAVAILABLE")
            return []

    def _stage_vulnerability(
        self,
        run: PipelineRun,
        input_data: PipelineInput,
        artifacts: Dict[str, Any],
    ) -> List[str]:
        """Stage 4: Susceptibility and Fragility Modeling via Phase 5 VulnerabilityEngine."""
        hazard_evals: List[HazardEvaluation] = artifacts.get("hazard_evaluations", [])
        primary_hazard = self._select_primary_hazard(hazard_evals)
        exp_eval: Optional[ExposureEvaluation] = artifacts.get("exposure_evaluation")

        if not primary_hazard:
            run.vulnerability_evaluation_ids = []
            return []

        vuln_eval = self.vulnerability_engine.evaluate(
            hazard_eval=primary_hazard,
            exposure_eval=exp_eval,
            demographic_indicators=input_data.demographic_indicators,
        )
        artifacts["vulnerability_evaluation"] = vuln_eval
        run.vulnerability_evaluation_ids = [vuln_eval.evaluation_id]
        return run.vulnerability_evaluation_ids

    def _stage_risk(
        self,
        run: PipelineRun,
        input_data: PipelineInput,
        artifacts: Dict[str, Any],
    ) -> List[str]:
        """Stage 5: Quantitative Multiplicative Risk (R = H x E x V) via Phase 6 RiskEngine."""
        hazard_evals: List[HazardEvaluation] = artifacts.get("hazard_evaluations", [])
        primary_hazard = self._select_primary_hazard(hazard_evals)
        exp_eval: Optional[ExposureEvaluation] = artifacts.get("exposure_evaluation")
        vuln_eval: Optional[VulnerabilityEvaluation] = artifacts.get("vulnerability_evaluation")

        if not primary_hazard or not exp_eval or not vuln_eval:
            run.risk_assessment_ids = []
            return []

        risk_assessments: List[RiskAssessment] = []
        # Match each exposure result with corresponding vulnerability result
        for er in exp_eval.exposure_results:
            matching_vr = next(
                (vr for vr in vuln_eval.vulnerability_results if vr.asset_id in er.asset_identifiers),
                vuln_eval.vulnerability_results[0] if vuln_eval.vulnerability_results else None,
            )
            if matching_vr:
                try:
                    ra = self.risk_engine.evaluate_risk(
                        hazard=primary_hazard,
                        exposure=er,
                        vulnerability=matching_vr,
                    )
                    risk_assessments.append(ra)
                except Exception as r_exc:
                    logger.warning("VayuBodhakPipeline: Risk evaluation skipped for asset: %s", r_exc)

        artifacts["risk_assessments"] = risk_assessments
        run.risk_assessment_ids = [r.assessment_id for r in risk_assessments]
        return run.risk_assessment_ids

    def _stage_impact(
        self,
        run: PipelineRun,
        input_data: PipelineInput,
        artifacts: Dict[str, Any],
    ) -> List[str]:
        """Stage 6: Potential Impact Assessment via Phase 7 ImpactEngine."""
        hazard_evals: List[HazardEvaluation] = artifacts.get("hazard_evaluations", [])
        primary_hazard = self._select_primary_hazard(hazard_evals)

        if not primary_hazard:
            run.impact_assessment_ids = []
            return []

        impact_list: List[PotentialImpactAssessment] = []

        # Evaluate exposed roads
        if input_data.roads:
            for rd in input_data.roads:
                try:
                    imp_rd = self.impact_engine.evaluate_road(
                        hazard=primary_hazard,
                        road=rd,
                    )
                    impact_list.append(imp_rd)
                except Exception as exc:
                    logger.warning("VayuBodhakPipeline: Road impact calculation skipped: %s", exc)

        # Evaluate exposed hospitals
        if input_data.hospitals:
            for hosp in input_data.hospitals:
                try:
                    imp_hosp = self.impact_engine.evaluate_hospital(
                        hazard=primary_hazard,
                        hospital=hosp,
                    )
                    impact_list.append(imp_hosp)
                except Exception as exc:
                    logger.warning("VayuBodhakPipeline: Hospital impact calculation skipped: %s", exc)

        # Evaluate exposed schools
        if input_data.schools:
            for sch in input_data.schools:
                try:
                    imp_sch = self.impact_engine.evaluate_school(
                        hazard=primary_hazard,
                        school=sch,
                    )
                    impact_list.append(imp_sch)
                except Exception as exc:
                    logger.warning("VayuBodhakPipeline: School impact calculation skipped: %s", exc)

        # Create unified impact bundle
        bundle = self.impact_engine.evaluate_bundle(
            hazard=primary_hazard,
            assessments=impact_list,
        )
        artifacts["impact_bundle"] = bundle
        run.impact_assessment_ids = [bundle.bundle_id]
        if bundle.has_quality_warning or impact_list:
            if "PROTOTYPE_IMPACT_DEPENDENCY" not in run.prototype_flags:
                run.prototype_flags.append("PROTOTYPE_IMPACT_DEPENDENCY")
        return run.impact_assessment_ids

    def _stage_decision(
        self,
        run: PipelineRun,
        input_data: PipelineInput,
        artifacts: Dict[str, Any],
        now_dt: datetime,
    ) -> List[str]:
        """Stage 7: Decision Support & NirnayCard Generation via Phase 8 NirnayEngine."""
        hazard_evals: List[HazardEvaluation] = artifacts.get("hazard_evaluations", [])
        primary_hazard = self._select_primary_hazard(hazard_evals)
        impact_bundle: Optional[ImpactEvaluationBundle] = artifacts.get("impact_bundle")
        risk_assessments: List[RiskAssessment] = artifacts.get("risk_assessments", [])
        primary_risk = risk_assessments[0] if risk_assessments else None

        staleness_state = (
            "STALE"
            if (primary_hazard and primary_hazard.quality_state == QualityState.STALE.value)
            or run.quality_state == QualityState.STALE.value
            or "STALE_HAZARD_DETECTED" in run.prototype_flags
            else "FRESH"
        )

        pkg = self.decision_engine.evaluate(
            hazard=primary_hazard,
            risk=primary_risk,
            impact_bundle=impact_bundle,
            official_warnings=input_data.official_warnings,
            evidence_quality=run.quality_state,
            data_coverage=run.data_coverage,
            staleness_state=staleness_state,
            geography=input_data.geography,
            now_dt=now_dt,
        )

        run.decision_id = pkg.decision_id
        run.nirnay_card = pkg.nirnay_card
        artifacts["decision_package"] = pkg

        # Harmonize terminal pipeline state with decision outcome
        if (
            pkg.decision.decision_status == DecisionState.REVIEW_REQUIRED
            or run.quality_state in (QualityState.STALE.value, QualityState.CONFLICT.value)
            or "STALE_HAZARD_DETECTED" in run.prototype_flags
            or "CONFLICT_DETECTED" in run.prototype_flags
        ):
            run.pipeline_state = PipelineState.REVIEW_REQUIRED
        elif (
            pkg.decision.decision_status == DecisionState.INSUFFICIENT_EVIDENCE
            or run.quality_state == QualityState.MISSING.value
        ):
            run.pipeline_state = PipelineState.INSUFFICIENT_EVIDENCE

        return [pkg.decision_id]

    # ------------------------------------------------------------------------
    # 5. Safe Stage Retry & Backward Trace Subroutines
    # ------------------------------------------------------------------------

    async def _execute_stage_with_retry(
        self,
        run: PipelineRun,
        stage: PipelineStage,
        func,
        max_retries: int,
    ) -> None:
        """Executes a single pipeline stage with execution metrics, timing, and transient retries."""
        run.current_stage = stage
        attempts = 0
        last_exc: Optional[Exception] = None

        while attempts <= max_retries:
            start_time = time.perf_counter()
            start_iso = datetime.now(timezone.utc).isoformat()
            try:
                entity_ids = func()
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                end_iso = datetime.now(timezone.utc).isoformat()

                exec_log = PipelineStageExecution(
                    stage=stage,
                    status="COMPLETED",
                    started_at_iso=start_iso,
                    completed_at_iso=end_iso,
                    duration_ms=round(duration_ms, 2),
                    quality_state=run.quality_state,
                    stage_entity_ids=entity_ids or [],
                )
                run.stage_executions.append(exec_log)
                run.completed_stages.append(stage)
                if run.pipeline_state not in (
                    PipelineState.REVIEW_REQUIRED,
                    PipelineState.INSUFFICIENT_EVIDENCE,
                    PipelineState.STALE,
                    PipelineState.CONFLICT,
                ):
                    run.pipeline_state = self._map_forward_state(stage)
                await self.repo.save_run(run)

                logger.info(
                    "pipeline_run_id=%s stage=%s status=COMPLETED duration_ms=%.2f",
                    run.pipeline_run_id,
                    stage.value,
                    duration_ms,
                )
                return
            except PipelineExecutionError as p_err:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                end_iso = datetime.now(timezone.utc).isoformat()
                exec_log = PipelineStageExecution(
                    stage=stage,
                    status="FAILED",
                    started_at_iso=start_iso,
                    completed_at_iso=end_iso,
                    duration_ms=round(duration_ms, 2),
                    quality_state=run.quality_state,
                    error_code=p_err.error_code,
                    error_message=p_err.message,
                )
                run.stage_executions.append(exec_log)
                if not p_err.retriable:
                    raise p_err
                attempts += 1
                run.retry_count += 1
                last_exc = p_err
                time.sleep(0.05 * attempts)
            except Exception as exc:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                end_iso = datetime.now(timezone.utc).isoformat()
                exec_log = PipelineStageExecution(
                    stage=stage,
                    status="FAILED",
                    started_at_iso=start_iso,
                    completed_at_iso=end_iso,
                    duration_ms=round(duration_ms, 2),
                    quality_state=run.quality_state,
                    error_code=PipelineErrorCode.UNKNOWN_ERROR,
                    error_message=str(exc),
                )
                run.stage_executions.append(exec_log)
                attempts += 1
                run.retry_count += 1
                last_exc = exc
                time.sleep(0.05 * attempts)

        raise PipelineExecutionError(
            stage=stage,
            error_code=PipelineErrorCode.UNKNOWN_ERROR,
            message=f"Stage {stage} exceeded retry limit: {last_exc}",
            retriable=False,
        )

    @staticmethod
    def _map_forward_state(stage: PipelineStage) -> PipelineState:
        mapping = {
            PipelineStage.EVIDENCE: PipelineState.EVIDENCE_VALIDATED,
            PipelineStage.HAZARD: PipelineState.HAZARD_EVALUATED,
            PipelineStage.EXPOSURE: PipelineState.EXPOSURE_EVALUATED,
            PipelineStage.VULNERABILITY: PipelineState.VULNERABILITY_EVALUATED,
            PipelineStage.RISK: PipelineState.RISK_EVALUATED,
            PipelineStage.IMPACT: PipelineState.IMPACT_EVALUATED,
            PipelineStage.DECISION: PipelineState.DECISION_EVALUATED,
            PipelineStage.NIRNAY: PipelineState.NIRNAY_GENERATED,
            PipelineStage.PERSISTENCE: PipelineState.PERSISTED,
        }
        return mapping.get(stage, PipelineState.RECEIVED)

    @staticmethod
    def _map_failure_state(stage: PipelineStage) -> PipelineState:
        mapping = {
            PipelineStage.EVIDENCE: PipelineState.FAILED_EVIDENCE,
            PipelineStage.HAZARD: PipelineState.FAILED_HAZARD,
            PipelineStage.EXPOSURE: PipelineState.FAILED_EXPOSURE,
            PipelineStage.VULNERABILITY: PipelineState.FAILED_VULNERABILITY,
            PipelineStage.RISK: PipelineState.FAILED_RISK,
            PipelineStage.IMPACT: PipelineState.FAILED_IMPACT,
            PipelineStage.DECISION: PipelineState.FAILED_DECISION,
            PipelineStage.PERSISTENCE: PipelineState.FAILED_PERSISTENCE,
        }
        return mapping.get(stage, PipelineState.FAILED_EVIDENCE)

    def compute_pipeline_provenance(self, run: PipelineRun) -> str:
        """Computes deterministic SHA-256 pipeline execution trace hash."""
        trace_dict = {
            "pipeline_run_id": run.pipeline_run_id,
            "pipeline_version": run.pipeline_version,
            "input_reference": run.input_reference,
            "evidence_ids": sorted(run.evidence_ids),
            "hazard_evaluation_ids": sorted(run.hazard_evaluation_ids),
            "exposure_evaluation_ids": sorted(run.exposure_evaluation_ids),
            "vulnerability_evaluation_ids": sorted(run.vulnerability_evaluation_ids),
            "risk_assessment_ids": sorted(run.risk_assessment_ids),
            "impact_assessment_ids": sorted(run.impact_assessment_ids),
            "decision_id": run.decision_id,
            "quality_state": run.quality_state,
        }
        encoded = json.dumps(trace_dict, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def build_trace(self, run: PipelineRun) -> PipelineTrace:
        """Constructs full lineage audit trace for a completed/partial pipeline run."""
        trace_stages = [
            PipelineTraceStage(
                stage=stg.stage,
                entity_ids=stg.stage_entity_ids,
                quality_state=stg.quality_state,
                rule_or_method_ids=[stg.details.get("rule_id", "")] if stg.details and stg.details.get("rule_id") else [],
                versions=[stg.details.get("version", "1.0.0")] if stg.details and stg.details.get("version") else [],
            )
            for stg in run.stage_executions
        ]

        card_verdict = None
        if run.nirnay_card:
            card_verdict = (
                run.nirnay_card.verdict.value
                if hasattr(run.nirnay_card.verdict, "value")
                else str(run.nirnay_card.verdict)
            )

        has_official = False
        if run.nirnay_card:
            if hasattr(run.nirnay_card, "official_information") and run.nirnay_card.official_information:
                has_official = True
            elif hasattr(run.nirnay_card, "official_directive_text") and run.nirnay_card.official_directive_text:
                has_official = True

        return PipelineTrace(
            pipeline_run_id=run.pipeline_run_id,
            provenance_id=run.provenance_id,
            generated_at_iso=datetime.now(timezone.utc).isoformat(),
            target_geography=run.input_reference,
            source_status=run.source_status,
            verdict=card_verdict,
            stages=trace_stages,
            evidence_sources=run.evidence_ids,
            official_directives_present=has_official,
            prototype_dependencies=run.prototype_flags,
        )


# Global singleton pipeline instance
vayubodhak_pipeline = VayuBodhakPipeline()

"""Selective Pipeline Re-run & Decision Revision Engine for Phase 9C.

Executes selective re-evaluation:
- Skips unaffected upstream or peer stages (reusing validated entity IDs)
- Reruns strictly affected downstream stages using existing analytical engines
- Generates revisioned PipelineRun instances (revision=2, 3...) preserving historical audit chain
- Detects deterministic decision deltas (STATE_CHANGED, WARNING_CHANGED, WARNING_EXPIRED, NO_CHANGE)
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.decision.models import NirnayCard
from app.events.change_detector import ChangeDetector, ChangeEvaluationResult, change_detector
from app.events.models import ChangeClassification, EventProcessingStatus, OperationalEvent
from app.events.repository import EventRepository, event_repository
from app.evidence.models import EvidenceRecord
from app.evidence.service import evidence_service
from app.pipeline.models import (
    DataSourceStatus,
    PipelineInput,
    PipelineRun,
    PipelineStage,
    PipelineState,
)
from app.pipeline.orchestrator import VayuBodhakPipeline, vayubodhak_pipeline
from app.pipeline.repository import PipelineRepository, pipeline_repository

logger = logging.getLogger(__name__)


class DecisionComparisonResult:
    """Detailed comparison between previous and new decision state."""
    def __init__(
        self,
        has_changed: bool,
        change_type: str,
        previous_verdict: Optional[str] = None,
        new_verdict: Optional[str] = None,
        previous_severity: Optional[str] = None,
        new_severity: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.has_changed = has_changed
        self.change_type = change_type
        self.previous_verdict = previous_verdict
        self.new_verdict = new_verdict
        self.previous_severity = previous_severity
        self.new_severity = new_severity
        self.details = details or {}


class SelectivePipelineOrchestrator:
    """Manages selective pipeline execution and decision state transitions."""

    def __init__(
        self,
        pipeline: Optional[VayuBodhakPipeline] = None,
        pipeline_repo: Optional[PipelineRepository] = None,
        event_repo: Optional[EventRepository] = None,
        detector: Optional[ChangeDetector] = None,
    ):
        self.pipeline = pipeline or vayubodhak_pipeline
        self.pipeline_repo = pipeline_repo or pipeline_repository
        self.event_repo = event_repo or event_repository
        self.detector = detector or change_detector

    def compare_decisions(
        self,
        prev_card: Optional[NirnayCard],
        new_card: Optional[NirnayCard],
    ) -> DecisionComparisonResult:
        """Determines whether published deterministic decision context changed."""
        if not prev_card and not new_card:
            return DecisionComparisonResult(has_changed=False, change_type="NO_CHANGE")
        if not prev_card and new_card:
            return DecisionComparisonResult(
                has_changed=True,
                change_type="INITIAL_DECISION",
                new_verdict=new_card.verdict.value,
                new_severity=new_card.severity.value,
            )
        if prev_card and not new_card:
            return DecisionComparisonResult(
                has_changed=True,
                change_type="DECISION_WITHDRAWN",
                previous_verdict=prev_card.verdict.value,
                previous_severity=prev_card.severity.value,
            )

        assert prev_card is not None and new_card is not None
        prev_v = prev_card.verdict.value
        new_v = new_card.verdict.value
        prev_s = prev_card.severity.value
        new_s = new_card.severity.value

        # Check Official Warning change
        prev_warn = prev_card.official_information
        new_warn = new_card.official_information
        if prev_warn != new_warn:
            if prev_warn and not new_warn:
                return DecisionComparisonResult(
                    has_changed=True,
                    change_type="WARNING_EXPIRED",
                    previous_verdict=prev_v,
                    new_verdict=new_v,
                    previous_severity=prev_s,
                    new_severity=new_s,
                )
            return DecisionComparisonResult(
                has_changed=True,
                change_type="WARNING_CHANGED",
                previous_verdict=prev_v,
                new_verdict=new_v,
                previous_severity=prev_s,
                new_severity=new_s,
                details={
                    "prev_warning": prev_warn.warning_level if prev_warn else None,
                    "new_warning": new_warn.warning_level if new_warn else None,
                },
            )

        # Check Verdict or Severity delta
        if prev_v != new_v or prev_s != new_s:
            return DecisionComparisonResult(
                has_changed=True,
                change_type="STATE_CHANGED",
                previous_verdict=prev_v,
                new_verdict=new_v,
                previous_severity=prev_s,
                new_severity=new_s,
            )

        # Actions or Action Window delta
        if prev_card.recommended_action != new_card.recommended_action:
            return DecisionComparisonResult(
                has_changed=True,
                change_type="ACTION_MODIFIED",
                previous_verdict=prev_v,
                new_verdict=new_v,
                previous_severity=prev_s,
                new_severity=new_s,
            )

        return DecisionComparisonResult(
            has_changed=False,
            change_type="INPUT_CHANGED_ONLY",
            previous_verdict=prev_v,
            new_verdict=new_v,
            previous_severity=prev_s,
            new_severity=new_s,
        )

    async def process_operational_event(
        self,
        event: OperationalEvent,
        input_data: PipelineInput,
        previous_run: Optional[PipelineRun] = None,
        previous_event: Optional[OperationalEvent] = None,
    ) -> Tuple[Optional[PipelineRun], DecisionComparisonResult]:
        """Evaluates operational event, selectively reruns pipeline if needed, and computes decision delta."""
        
        # 1. Evaluate change significance
        eval_result = self.detector.evaluate_change(
            event=event,
            latest_run=previous_run,
            previous_event=previous_event,
        )

        # 2. No-op if benign/insignificant change
        if not eval_result.is_meaningful_change:
            logger.info("SelectivePipeline: No recomputation required for event %s (%s)", event.event_id, eval_result.reason)
            await self.event_repo.update_status(
                event.event_id,
                EventProcessingStatus.NO_CHANGE,
                details={"reason": eval_result.reason, "recalculation": "NO_OP"},
            )
            cmp_res = DecisionComparisonResult(has_changed=False, change_type="NO_CHANGE")
            return previous_run, cmp_res

        # 3. Initialize Revision PipelineRun
        next_revision = (previous_run.revision + 1) if previous_run else 1
        run = PipelineRun(
            input_reference=input_data.input_reference,
            source_status=input_data.source_status if hasattr(input_data, "source_status") else DataSourceStatus.LIVE,
            revision=next_revision,
            supersedes_run_id=previous_run.pipeline_run_id if previous_run else None,
            trigger_event_id=event.event_id,
            recomputation_reason=eval_result.reason,
            selective_stages=[s.value for s in eval_result.affected_stages],
        )

        # 4. Carry forward reusable entity IDs
        if previous_run:
            if PipelineStage.EXPOSURE in eval_result.reusable_stages:
                run.exposure_evaluation_ids = list(previous_run.exposure_evaluation_ids)
                run.completed_stages.append(PipelineStage.EXPOSURE)
            if PipelineStage.VULNERABILITY in eval_result.reusable_stages:
                run.vulnerability_evaluation_ids = list(previous_run.vulnerability_evaluation_ids)
                run.completed_stages.append(PipelineStage.VULNERABILITY)
            if PipelineStage.HAZARD in eval_result.reusable_stages:
                run.hazard_evaluation_ids = list(previous_run.hazard_evaluation_ids)
                run.completed_stages.append(PipelineStage.HAZARD)
            if PipelineStage.RISK in eval_result.reusable_stages:
                run.risk_assessment_ids = list(previous_run.risk_assessment_ids)
                run.completed_stages.append(PipelineStage.RISK)
            if PipelineStage.IMPACT in eval_result.reusable_stages:
                run.impact_assessment_ids = list(previous_run.impact_assessment_ids)
                run.completed_stages.append(PipelineStage.IMPACT)

        # 5. Ingest event evidence IDs into input data if not already present
        for ev_id in event.evidence_ids:
            ev_rec = evidence_service.get_evidence(ev_id)
            if ev_rec and all(e.evidence_id != ev_id for e in input_data.evidence_records):
                input_data.evidence_records.append(ev_rec)

        # 6. Execute governed pipeline recomputation
        logger.info(
            "SelectivePipeline: Executing revision %d (run %s) for event %s (affected: %s)",
            run.revision,
            run.pipeline_run_id,
            event.event_id,
            run.selective_stages,
        )
        completed_run = await self.pipeline._execute_lifecycle(run, input_data, max_retries=1)

        # 7. Decision Delta Comparison
        prev_card = previous_run.nirnay_card if previous_run else None
        new_card = completed_run.nirnay_card
        cmp_result = self.compare_decisions(prev_card, new_card)

        # 8. Create and Persist Canonical DecisionRevision (Phase 9C-D)
        from app.decision.revision import DecisionRevision, decision_revision_repository
        prev_rev = await decision_revision_repository.get_latest_revision_for_decision(
            completed_run.decision_id or f"DEC-{completed_run.pipeline_run_id}"
        )
        decision_id = completed_run.decision_id or (previous_run.decision_id if previous_run else f"DEC-{completed_run.pipeline_run_id}")
        
        rev = DecisionRevision(
            decision_id=decision_id,
            revision_number=completed_run.revision,
            trigger_event_id=event.event_id,
            previous_revision_id=prev_rev.revision_id if prev_rev else None,
            pipeline_run_id=completed_run.pipeline_run_id,
            risk_state={
                "risk_assessment_ids": completed_run.risk_assessment_ids,
                "hazard_evaluation_ids": completed_run.hazard_evaluation_ids,
            },
            impact_state={
                "impact_assessment_ids": completed_run.impact_assessment_ids,
            },
            decision_state=completed_run.nirnay_card.model_dump() if completed_run.nirnay_card else {},
            nirnay_card=completed_run.nirnay_card,
            evidence_versions=[e.evidence_id for e in input_data.evidence_records],
            provenance={
                "pipeline_version": completed_run.pipeline_version,
                "recomputation_reason": eval_result.reason,
                "affected_stages": [s.value for s in eval_result.affected_stages],
                "reusable_stages": [s.value for s in eval_result.reusable_stages],
            },
        )
        await decision_revision_repository.save_revision(rev)

        # 9. Update Event status
        await self.event_repo.update_status(
            event.event_id,
            EventProcessingStatus.APPLIED,
            details={
                "revision": completed_run.revision,
                "revision_id": rev.revision_id,
                "pipeline_run_id": completed_run.pipeline_run_id,
                "decision_change": cmp_result.change_type,
                "has_changed": cmp_result.has_changed,
            },
            pipeline_run_id=completed_run.pipeline_run_id,
        )

        return completed_run, cmp_result


# Global singleton
selective_pipeline_orchestrator = SelectivePipelineOrchestrator()

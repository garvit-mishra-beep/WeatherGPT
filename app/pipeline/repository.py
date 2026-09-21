"""Async database repository for Phase 9A Pipeline Runs.

Provides durable PostgreSQL persistence and auditable retrieval for:
- Pipeline Runs (`pipeline_runs` table)
- Stage execution logs and metrics
- Backward lineage tracing

Durability Guarantee & Fallback Disclosure:
- When connected to a healthy PostgreSQL session: `is_durable = True`, `durability_status = "PERSISTENT_POSTGRESQL"`.
- When database is unreachable or session is None: `is_durable = False`, `durability_status = "EPHEMERAL_IN_MEMORY_FALLBACK"`.
  In-memory fallback is explicitly disclosed as non-durable.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.pipeline import PipelineRunRecordDB
from app.db.repositories.base import BaseRepository
from app.pipeline.models import (
    DataSourceStatus,
    PipelineRun,
    PipelineStage,
    PipelineState,
    PipelineTrace,
    PipelineTraceStage,
)

logger = logging.getLogger(__name__)

DURABILITY_STATUS_PERSISTENT = "PERSISTENT_POSTGRESQL"
DURABILITY_STATUS_EPHEMERAL = "EPHEMERAL_IN_MEMORY_FALLBACK"


class PipelineRepository(BaseRepository[PipelineRunRecordDB]):
    """Async repository for durable pipeline runs and backward lineage traces."""

    def __init__(self, session: Optional[AsyncSession] = None):
        super().__init__(session=session, model=PipelineRunRecordDB)
        self._in_memory_runs: Dict[str, PipelineRun] = {}
        self._in_memory_hash_index: Dict[str, str] = {}  # input_hash -> pipeline_run_id
        self._db_unavailable: bool = (session is None)
        self._last_db_error: Optional[str] = None

    @property
    def is_durable(self) -> bool:
        """Returns True ONLY if an active PostgreSQL session is attached and operating."""
        return self.session is not None and not self._db_unavailable

    @property
    def durability_status(self) -> str:
        """Explicit label disclosing whether writes are durable or ephemeral in-memory."""
        return DURABILITY_STATUS_PERSISTENT if self.is_durable else DURABILITY_STATUS_EPHEMERAL

    def bind_session(self, session: AsyncSession) -> None:
        """Dynamically binds an active AsyncSession to the repository."""
        self.session = session
        self._db_unavailable = False
        self._last_db_error = None

    def simulate_db_disconnect(self) -> None:
        """Simulate database disconnection for testing fallback behavior."""
        self._db_unavailable = True
        self._last_db_error = "SIMULATED_DB_DISCONNECT"

    async def save_run(self, run: PipelineRun) -> PipelineRun:
        """Saves or updates a PipelineRun record in PostgreSQL or ephemeral in-memory fallback."""
        run.durability_label = self.durability_status

        # Always update in-memory cache for fast lookups and fallback resilience
        self._in_memory_runs[run.pipeline_run_id] = run
        if run.input_hash:
            self._in_memory_hash_index[run.input_hash] = run.pipeline_run_id

        if not self.is_durable:
            logger.info(
                "PipelineRepository: Running in %s mode for run %s",
                self.durability_status,
                run.pipeline_run_id,
            )
            return run

        try:
            started_dt = datetime.fromisoformat(run.started_at_iso)
            completed_dt = (
                datetime.fromisoformat(run.completed_at_iso)
                if run.completed_at_iso
                else None
            )

            # Check if record exists
            stmt = select(PipelineRunRecordDB).where(
                PipelineRunRecordDB.pipeline_run_id == run.pipeline_run_id
            )
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()

            stage_exec_payload = [se.model_dump() for se in run.stage_executions]
            card_payload = run.nirnay_card.model_dump() if run.nirnay_card else None

            if existing:
                existing.completed_at = completed_dt
                existing.pipeline_state = run.pipeline_state.value
                existing.current_stage = (
                    run.current_stage.value if run.current_stage else None
                )
                existing.failed_stage = (
                    run.failed_stage.value if run.failed_stage else None
                )
                existing.completed_stages = [s.value for s in run.completed_stages]
                existing.evidence_ids = run.evidence_ids
                existing.hazard_evaluation_ids = run.hazard_evaluation_ids
                existing.exposure_evaluation_ids = run.exposure_evaluation_ids
                existing.vulnerability_evaluation_ids = run.vulnerability_evaluation_ids
                existing.risk_assessment_ids = run.risk_assessment_ids
                existing.impact_assessment_ids = run.impact_assessment_ids
                existing.decision_id = run.decision_id
                existing.quality_state = run.quality_state
                existing.data_coverage = run.data_coverage
                existing.prototype_flags = run.prototype_flags
                existing.provenance_id = run.provenance_id
                existing.error_code = run.error_code.value if run.error_code else None
                existing.error_message = run.error_message
                existing.retry_count = run.retry_count
                existing.stage_executions = stage_exec_payload
                existing.nirnay_card_payload = card_payload
                existing.full_payload = run.model_dump()
            else:
                db_record = PipelineRunRecordDB(
                    pipeline_run_id=run.pipeline_run_id,
                    pipeline_version=run.pipeline_version,
                    started_at=started_dt,
                    completed_at=completed_dt,
                    input_type=run.input_type,
                    input_reference=run.input_reference,
                    input_hash=run.input_hash,
                    source_status=run.source_status.value,
                    pipeline_state=run.pipeline_state.value,
                    current_stage=run.current_stage.value if run.current_stage else None,
                    failed_stage=run.failed_stage.value if run.failed_stage else None,
                    completed_stages=[s.value for s in run.completed_stages],
                    evidence_ids=run.evidence_ids,
                    hazard_evaluation_ids=run.hazard_evaluation_ids,
                    exposure_evaluation_ids=run.exposure_evaluation_ids,
                    vulnerability_evaluation_ids=run.vulnerability_evaluation_ids,
                    risk_assessment_ids=run.risk_assessment_ids,
                    impact_assessment_ids=run.impact_assessment_ids,
                    decision_id=run.decision_id,
                    quality_state=run.quality_state,
                    data_coverage=run.data_coverage,
                    prototype_flags=run.prototype_flags,
                    provenance_id=run.provenance_id,
                    error_code=run.error_code.value if run.error_code else None,
                    error_message=run.error_message,
                    retry_count=run.retry_count,
                    stage_executions=stage_exec_payload,
                    nirnay_card_payload=card_payload,
                    full_payload=run.model_dump(),
                )
                self.session.add(db_record)

            await self.session.commit()
            return run
        except Exception as exc:
            logger.warning(
                "PipelineRepository: DB write failed (%s); falling back to ephemeral in-memory storage.",
                exc,
            )
            self._db_unavailable = True
            self._last_db_error = str(exc)
            run.durability_label = DURABILITY_STATUS_EPHEMERAL
            return run

    async def get_run(self, pipeline_run_id: str) -> Optional[PipelineRun]:
        """Retrieves a PipelineRun by its canonical identifier."""
        # Check in-memory store first
        if pipeline_run_id in self._in_memory_runs:
            return self._in_memory_runs[pipeline_run_id]

        if not self.is_durable:
            return None

        try:
            stmt = select(PipelineRunRecordDB).where(
                PipelineRunRecordDB.pipeline_run_id == pipeline_run_id
            )
            result = await self.session.execute(stmt)
            record = result.scalar_one_or_none()
            if not record or not record.full_payload:
                return None
            run = PipelineRun.model_validate(record.full_payload)
            self._in_memory_runs[run.pipeline_run_id] = run
            return run
        except Exception as exc:
            logger.warning("PipelineRepository: DB read failed (%s)", exc)
            return None

    async def get_by_input_hash(self, input_hash: str) -> Optional[PipelineRun]:
        """Finds existing run by input hash for idempotency check."""
        if input_hash in self._in_memory_hash_index:
            run_id = self._in_memory_hash_index[input_hash]
            return self._in_memory_runs.get(run_id)

        if not self.is_durable:
            return None

        try:
            stmt = select(PipelineRunRecordDB).where(
                PipelineRunRecordDB.input_hash == input_hash
            ).order_by(desc(PipelineRunRecordDB.started_at))
            result = await self.session.execute(stmt)
            record = result.scalars().first()
            if not record or not record.full_payload:
                return None
            run = PipelineRun.model_validate(record.full_payload)
            self._in_memory_runs[run.pipeline_run_id] = run
            self._in_memory_hash_index[input_hash] = run.pipeline_run_id
            return run
        except Exception as exc:
            logger.warning("PipelineRepository: DB hash query failed (%s)", exc)
            return None

    async def get_latest_run(self) -> Optional[PipelineRun]:
        """Retrieves the most recent PipelineRun across in-memory and durable storage."""
        if self._in_memory_runs:
            sorted_runs = sorted(self._in_memory_runs.values(), key=lambda r: r.started_at_iso, reverse=True)
            return sorted_runs[0]
        if not self.is_durable:
            return None
        try:
            stmt = select(PipelineRunRecordDB).order_by(desc(PipelineRunRecordDB.started_at)).limit(1)
            result = await self.session.execute(stmt)
            record = result.scalars().first()
            if not record or not record.full_payload:
                return None
            return PipelineRun.model_validate(record.full_payload)
        except Exception as exc:
            logger.warning("PipelineRepository: get_latest_run DB read failed (%s)", exc)
            return None

    def clear(self) -> None:
        """Clears in-memory storage for test isolation."""
        self._in_memory_runs.clear()
        self._in_memory_hash_index.clear()
        self._db_unavailable = (self.session is None)
        self._last_db_error = None


# Global singleton repository instance
pipeline_repository = PipelineRepository()

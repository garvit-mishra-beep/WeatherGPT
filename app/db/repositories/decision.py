"""Async database repository for Phase 8 Decision Support & Nirnay Engine.

Provides durable PostgreSQL persistence and auditable retrieval for:
1. Decision Assessments (`decision_assessments` table)
2. State Transition Lineage (`decision_transition_history` table)
3. Operational Human Verification Sign-Offs (`decision_verifications` table)

Durability Guarantee & Fallback Disclosure:
- When connected to a healthy PostgreSQL session: `is_durable = True`, `durability_status = "PERSISTENT_POSTGRESQL"`.
- When database is unreachable or session is None: `is_durable = False`, `durability_status = "EPHEMERAL_IN_MEMORY_FALLBACK"`.
  In-memory fallback is explicitly disclosed as non-durable; records will NOT survive process restart.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.decision import (
    DecisionAssessmentRecordDB,
    DecisionHistoryRecordDB,
    DecisionVerificationRecordDB,
)
from app.db.repositories.base import BaseRepository
from app.decision.models import (
    ChangeReasonCode,
    DecisionChangeRecord,
    DecisionPackage,
    DecisionState,
    DecisionVerificationRecord,
)

logger = logging.getLogger(__name__)

DURABILITY_STATUS_PERSISTENT = "PERSISTENT_POSTGRESQL"
DURABILITY_STATUS_EPHEMERAL = "EPHEMERAL_IN_MEMORY_FALLBACK"


class DecisionRepository(BaseRepository[DecisionAssessmentRecordDB]):
    """Async repository for durable decision assessments, history, and verifications."""

    def __init__(self, session: Optional[AsyncSession] = None):
        super().__init__(session=session, model=DecisionAssessmentRecordDB)
        # In-memory fallback cache to ensure zero breakage when running in offline/mock mode
        self._in_memory_assessments: Dict[str, DecisionPackage] = {}
        self._in_memory_history: Dict[str, List[Dict[str, Any]]] = {}
        self._in_memory_verifications: Dict[str, List[DecisionVerificationRecord]] = {}
        self._db_unavailable: bool = (session is None)
        self._last_db_error: Optional[str] = None

    @property
    def is_durable(self) -> bool:
        """Returns True ONLY if active PostgreSQL session is attached and operating."""
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

    async def save_assessment(self, package: DecisionPackage, version: int = 1) -> DecisionPackage:
        """Saves a DecisionPackage to persistent database store."""
        self._in_memory_assessments[package.decision_id] = package

        if self.session is None:
            self._db_unavailable = True
            logger.warning(
                "DecisionRepository: Database session is None. "
                "Operating in EPHEMERAL non-durable in-memory fallback mode (durability_status='%s'). "
                "Assessment '%s' will NOT survive process restart.",
                self.durability_status,
                package.decision_id,
            )
            return package

        try:
            assessment_dt = datetime.fromisoformat(package.timestamp_iso.replace("Z", "+00:00"))
            record = DecisionAssessmentRecordDB(
                decision_id=package.decision_id,
                version=version,
                assessment_time=assessment_dt,
                expires_at=None,
                hazard_evaluation_id=package.decision.hazard_evaluation_id,
                exposure_id=package.decision.exposure_id,
                vulnerability_id=package.decision.vulnerability_id,
                risk_id=package.decision.risk_id,
                impact_id=package.decision.impact_id,
                decision_state=package.decision.decision_status.value,
                priority_class=package.recommendations[0].priority.value if package.recommendations else "ROUTINE",
                decision_conditions=package.decision.decision_conditions,
                eligible_actions=[a.model_dump() for a in package.decision.eligible_actions],
                prohibited_actions=package.decision.prohibited_actions,
                official_warning_ids=package.decision.official_warning_ids,
                method_ids=package.decision.method_ids,
                rule_ids=package.decision.method_ids,
                claim_ids=package.decision.claim_ids,
                evidence_quality=package.decision.evidence_quality,
                data_coverage=package.decision.data_coverage,
                staleness_state=package.decision.staleness_state,
                human_verification_required=package.decision.human_verification_required,
                verification_status=package.verification.get("verification_status", "NOT_REQUIRED"),
                provenance_id=package.decision.provenance_id,
                package_payload=package.model_dump(),
                created_at=datetime.now(timezone.utc),
            )
            self.session.add(record)
            await self.session.commit()
            self._db_unavailable = False
            self._last_db_error = None
        except Exception as e:
            self._db_unavailable = True
            self._last_db_error = str(e)
            logger.warning(
                "DecisionRepository: DB save_assessment failed (%s). "
                "Falling back to EPHEMERAL non-durable in-memory cache (durability_status='%s'). "
                "Assessment '%s' will NOT survive process restart.",
                e,
                self.durability_status,
                package.decision_id,
            )
            try:
                await self.session.rollback()
            except Exception:
                pass

        return package

    async def get_assessment(self, decision_id: str, bypass_cache: bool = False) -> Optional[DecisionPackage]:
        """Retrieves a stored DecisionPackage by decision_id.
        
        Args:
            decision_id: Target decision identifier.
            bypass_cache: If True, bypasses in-memory dictionary and queries PostgreSQL directly.
        """
        if not bypass_cache and decision_id in self._in_memory_assessments:
            return self._in_memory_assessments[decision_id]

        if self.session is not None:
            try:
                stmt = select(DecisionAssessmentRecordDB).where(DecisionAssessmentRecordDB.decision_id == decision_id)
                res = await self.session.execute(stmt)
                record = res.scalars().first()
                if record and record.package_payload:
                    pkg = DecisionPackage.model_validate(record.package_payload)
                    self._in_memory_assessments[decision_id] = pkg
                    return pkg
            except Exception as e:
                self._db_unavailable = True
                self._last_db_error = str(e)
                logger.warning("DecisionRepository: DB query failed: %s", e)

        return None if bypass_cache else self._in_memory_assessments.get(decision_id)

    async def record_history(
        self,
        change_record: DecisionChangeRecord,
        version: int = 1,
        changed_fields: Optional[List[str]] = None,
        rule_id: Optional[str] = None,
        rule_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persists a decision transition record to decision_transition_history."""
        hist_entry = {
            "id": f"HIST-{uuid.uuid4().hex[:8].upper()}",
            "decision_id": change_record.decision_id,
            "previous_decision_id": change_record.previous_decision_id,
            "version": version,
            "previous_state": change_record.previous_state.value if change_record.previous_state else None,
            "new_state": change_record.new_state.value,
            "change_reason": change_record.reason_code.value,
            "changed_fields": changed_fields or ["decision_status", "recommendations"],
            "reason_details": change_record.reason_details,
            "rule_id": rule_id,
            "rule_version": rule_version,
            "created_at": change_record.changed_at_iso,
        }

        if change_record.decision_id not in self._in_memory_history:
            self._in_memory_history[change_record.decision_id] = []
        self._in_memory_history[change_record.decision_id].append(hist_entry)

        if self.session is None:
            self._db_unavailable = True
            logger.warning(
                "DecisionRepository: Database session is None. "
                "Operating in EPHEMERAL non-durable in-memory fallback mode (durability_status='%s'). "
                "Transition record will NOT survive process restart.",
                self.durability_status,
            )
            return hist_entry

        try:
            created_dt = datetime.fromisoformat(change_record.changed_at_iso.replace("Z", "+00:00"))
            db_hist = DecisionHistoryRecordDB(
                id=hist_entry["id"],
                decision_id=change_record.decision_id,
                previous_decision_id=change_record.previous_decision_id,
                version=version,
                previous_state=hist_entry["previous_state"],
                new_state=hist_entry["new_state"],
                change_reason=hist_entry["change_reason"],
                changed_fields=hist_entry["changed_fields"],
                reason_details=hist_entry["reason_details"],
                rule_id=rule_id,
                rule_version=rule_version,
                created_at=created_dt,
            )
            self.session.add(db_hist)
            await self.session.commit()
            self._db_unavailable = False
            self._last_db_error = None
        except Exception as e:
            self._db_unavailable = True
            self._last_db_error = str(e)
            logger.warning(
                "DecisionRepository: DB history record failed (%s). "
                "Falling back to EPHEMERAL non-durable in-memory cache (durability_status='%s'). "
                "Transition record will NOT survive process restart.",
                e,
                self.durability_status,
            )
            try:
                await self.session.rollback()
            except Exception:
                pass

        return hist_entry

    async def get_history(self, decision_id: str, bypass_cache: bool = False) -> List[Dict[str, Any]]:
        """Retrieves persistent transition history for a decision lineage.
        
        Args:
            decision_id: Target decision identifier.
            bypass_cache: If True, queries PostgreSQL directly without checking memory cache.
        """
        if self.session is not None:
            try:
                stmt = (
                    select(DecisionHistoryRecordDB)
                    .where(DecisionHistoryRecordDB.decision_id == decision_id)
                    .order_by(desc(DecisionHistoryRecordDB.created_at))
                )
                res = await self.session.execute(stmt)
                rows = res.scalars().all()
                if rows:
                    records = [
                        {
                            "id": r.id,
                            "decision_id": r.decision_id,
                            "previous_decision_id": r.previous_decision_id,
                            "version": r.version,
                            "previous_state": r.previous_state,
                            "new_state": r.new_state,
                            "change_reason": r.change_reason,
                            "changed_fields": r.changed_fields,
                            "reason_details": r.reason_details,
                            "rule_id": r.rule_id,
                            "rule_version": r.rule_version,
                            "created_at": r.created_at.isoformat(),
                        }
                        for r in rows
                    ]
                    self._in_memory_history[decision_id] = records
                    return records
            except Exception as e:
                self._db_unavailable = True
                self._last_db_error = str(e)
                logger.warning("DecisionRepository: DB get_history failed: %s", e)

        return [] if bypass_cache else self._in_memory_history.get(decision_id, [])

    async def record_verification(
        self,
        record: DecisionVerificationRecord,
        verifier_reference: Optional[str] = None,
    ) -> DecisionVerificationRecord:
        """Persists a human verification sign-off record."""
        if record.decision_id not in self._in_memory_verifications:
            self._in_memory_verifications[record.decision_id] = []
        self._in_memory_verifications[record.decision_id].append(record)

        if self.session is None:
            self._db_unavailable = True
            logger.warning(
                "DecisionRepository: Database session is None. "
                "Operating in EPHEMERAL non-durable in-memory fallback mode (durability_status='%s'). "
                "Verification sign-off will NOT survive process restart.",
                self.durability_status,
            )
            return record

        ref = verifier_reference or getattr(record, "verifier_reference", None)
        try:
            verif_dt = datetime.fromisoformat(record.verified_at_iso.replace("Z", "+00:00"))
            db_verif = DecisionVerificationRecordDB(
                verification_id=record.verification_id,
                decision_id=record.decision_id,
                verifier_id=record.verifier_id,
                verifier_reference=ref,
                verification_status=record.verification_status,
                verification_note=record.verification_note,
                verified_at=verif_dt,
                created_at=datetime.now(timezone.utc),
            )
            self.session.add(db_verif)
            await self.session.commit()
            self._db_unavailable = False
            self._last_db_error = None
        except Exception as e:
            self._db_unavailable = True
            self._last_db_error = str(e)
            logger.warning(
                "DecisionRepository: DB record_verification failed (%s). "
                "Falling back to EPHEMERAL non-durable in-memory cache (durability_status='%s'). "
                "Verification will NOT survive process restart.",
                e,
                self.durability_status,
            )
            try:
                await self.session.rollback()
            except Exception:
                pass

        return record

    async def get_verifications(self, decision_id: str, bypass_cache: bool = False) -> List[DecisionVerificationRecord]:
        """Retrieves persistent human verifications for a decision.
        
        Args:
            decision_id: Target decision identifier.
            bypass_cache: If True, queries PostgreSQL directly without checking memory cache.
        """
        if self.session is not None:
            try:
                stmt = (
                    select(DecisionVerificationRecordDB)
                    .where(DecisionVerificationRecordDB.decision_id == decision_id)
                    .order_by(desc(DecisionVerificationRecordDB.verified_at))
                )
                res = await self.session.execute(stmt)
                rows = res.scalars().all()
                if rows:
                    verifs = [
                        DecisionVerificationRecord(
                            verification_id=r.verification_id,
                            decision_id=r.decision_id,
                            verifier_id=r.verifier_id,
                            verifier_reference=r.verifier_reference,
                            verification_status=r.verification_status,
                            verification_note=r.verification_note or "",
                            verified_at_iso=r.verified_at.isoformat(),
                        )
                        for r in rows
                    ]
                    self._in_memory_verifications[decision_id] = verifs
                    return verifs
            except Exception as e:
                self._db_unavailable = True
                self._last_db_error = str(e)
                logger.warning("DecisionRepository: DB get_verifications failed: %s", e)

        return [] if bypass_cache else self._in_memory_verifications.get(decision_id, [])


# Singleton instance for router and test usage
decision_repository = DecisionRepository()

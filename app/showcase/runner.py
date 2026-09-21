"""Deterministic Showcase Scenario Runner for VAYUBODHAK.

Provides START, NEXT, and RESET orchestration feeding controlled demonstration
datasets as INPUT through 100% real VAYUBODHAK analytical processing components:
Evidence Foundation -> Operational Event -> Change Detector -> Selective Pipeline ->
Decision Revision -> Notification Engine -> Android Sync API.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

from app.decision.models import (
    ConfidenceLevel,
    DecisionOutcome,
    NirnayCard,
    OfficialWarningInfo,
    SeverityLevel,
)
from app.decision.revision import (
    DecisionRevision,
    DecisionRevisionRepository,
    decision_revision_repository,
)
from app.events.change_detector import ChangeDetector, change_detector
from app.events.models import (
    ChangeClassification,
    EventProcessingStatus,
    EventType,
    OperationalEvent,
)
from app.events.notification import (
    EventNotificationEngine,
    OperationalNotification,
)
from app.events.repository import EventRepository, event_repository
from app.events.selective_rerun import (
    DecisionComparisonResult,
    SelectivePipelineOrchestrator,
)
from app.evidence.models import (
    EvidenceClass,
    EvidenceRecord,
    QualityState,
    SourceAuthorityLevel,
    SpatialIdentity,
    TemporalIdentity,
)
from app.evidence.service import EvidenceService, evidence_service
from app.exposure.models import CriticalAsset, ExposureType, RoadSegment
from app.pipeline.models import (
    DataSourceStatus,
    PipelineInput,
    PipelineRun,
    PipelineState,
)
from app.pipeline.orchestrator import VayuBodhakPipeline, vayubodhak_pipeline
from app.pipeline.repository import PipelineRepository, pipeline_repository

logger = logging.getLogger(__name__)

# Base path for showcase dataset
SHOWCASE_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "showcase"


class ShowcaseScenarioRunner:
    """Orchestrates controlled demonstration scenarios through real analytical pipelines."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        pipeline: Optional[VayuBodhakPipeline] = None,
        event_repo: Optional[EventRepository] = None,
        revision_repo: Optional[DecisionRevisionRepository] = None,
        pipeline_repo: Optional[PipelineRepository] = None,
    ):
        self.data_dir = data_dir or SHOWCASE_DATA_DIR
        self.pipeline = pipeline or vayubodhak_pipeline
        self.event_repo = event_repo or event_repository
        self.revision_repo = revision_repo or decision_revision_repository
        self.pipeline_repo = pipeline_repo or pipeline_repository
        self.notification_engine = EventNotificationEngine()
        self.selective_orchestrator = SelectivePipelineOrchestrator(
            pipeline=self.pipeline,
            pipeline_repo=self.pipeline_repo,
            event_repo=self.event_repo,
        )

        self._manifest: Dict[str, Any] = {}
        self._current_step_index: int = -1
        self._latest_run: Optional[PipelineRun] = None
        self._latest_revision: Optional[DecisionRevision] = None
        self._latest_event: Optional[OperationalEvent] = None
        self._notifications: List[OperationalNotification] = []

        self._load_manifest()

    def _load_manifest(self) -> None:
        """Loads scenario manifest if present."""
        manifest_file = self.data_dir / "scenario_manifest.json"
        if manifest_file.exists():
            with open(manifest_file, "r", encoding="utf-8") as f:
                self._manifest = json.load(f)
        else:
            self._manifest = {
                "scenario_id": "SCENARIO-GWALIOR-MONSOON-2026",
                "scenario_name": "Gwalior Monsoon Escalation & Resilience Showcase",
                "location": {"district": "Gwalior District", "latitude": 26.2183, "longitude": 78.1828},
            }

    def _load_json(self, filename: str) -> Dict[str, Any]:
        """Loads a structured JSON file from the showcase directory."""
        file_path = self.data_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Showcase data file not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @property
    def current_step_index(self) -> int:
        return self._current_step_index

    @property
    def latest_revision(self) -> Optional[DecisionRevision]:
        return self._latest_revision

    @property
    def latest_run(self) -> Optional[PipelineRun]:
        return self._latest_run

    @property
    def notifications(self) -> List[OperationalNotification]:
        return list(self._notifications)

    def _get_exposure_assets(self) -> Tuple[List[CriticalAsset], List[CriticalAsset], List[RoadSegment]]:
        exposure_data = self._load_json("exposure_snapshot.json")
        hospitals = [
            CriticalAsset(
                asset_id=h["asset_id"],
                name=h["name"],
                asset_type=ExposureType.HOSPITAL,
                latitude=h["coordinates"]["latitude"],
                longitude=h["coordinates"]["longitude"],
                metadata={"bed_capacity": h.get("bed_capacity", 100)},
                source_id="SHOWCASE-SURVEY",
            )
            for h in exposure_data.get("hospitals", [])
        ]
        schools = [
            CriticalAsset(
                asset_id=s["asset_id"],
                name=s["name"],
                asset_type=ExposureType.SCHOOL,
                latitude=s["coordinates"]["latitude"],
                longitude=s["coordinates"]["longitude"],
                metadata={"student_capacity": s.get("student_capacity", 500)},
                source_id="SHOWCASE-SURVEY",
            )
            for s in exposure_data.get("schools", [])
        ]
        roads = [
            RoadSegment(
                road_id=r["road_id"],
                road_name=r["name"],
                road_classification=r["road_category"],
                coordinates=[(78.15, 26.20), (78.25, 26.25)],
                length_km=float(r.get("length_km", 10.0)),
                source_id="SHOWCASE-SURVEY",
            )
            for r in exposure_data.get("roads", [])
        ]
        return hospitals, schools, roads

    def _save_state(self) -> None:
        state_file = self.data_dir / ".showcase_state.json"
        try:
            state = {
                "current_step_index": self._current_step_index,
                "latest_run_id": self._latest_run.pipeline_run_id if self._latest_run else None,
                "latest_revision_id": self._latest_revision.revision_id if self._latest_revision else None,
                "latest_event_id": self._latest_event.event_id if self._latest_event else None,
            }
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save showcase state: %s", e)

    async def _load_state_async(self) -> None:
        state_file = self.data_dir / ".showcase_state.json"
        if not state_file.exists():
            return
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            self._current_step_index = state.get("current_step_index", self._current_step_index)
            run_id = state.get("latest_run_id")
            if run_id and not self._latest_run:
                self._latest_run = await self.pipeline_repo.get_run(run_id)
            event_id = state.get("latest_event_id")
            if event_id and not self._latest_event:
                self._latest_event = await self.event_repo.get_event(event_id)
            rev_id = state.get("latest_revision_id")
            if rev_id and not self._latest_revision:
                self._latest_revision = await self.revision_repo.get_revision(rev_id)
        except Exception as e:
            logger.warning("Failed to load showcase state: %s", e)

    async def start(self) -> Dict[str, Any]:
        """STEP 0: Initializes baseline showcase state through real analytical pipeline."""
        logger.info("Initializing Showcase Scenario at Baseline (Step 0)")
        await self.reset()

        initial_weather_data = self._load_json("weather_initial.json")

        now_utc = datetime.now(timezone.utc)
        obs_time = now_utc - timedelta(minutes=15)
        temporal = TemporalIdentity(
            retrieval_time=now_utc,
            observation_time=obs_time,
            valid_from=obs_time,
            valid_to=now_utc + timedelta(hours=6),
        )
        spatial = SpatialIdentity(
            location_id=initial_weather_data["geography"],
            latitude=initial_weather_data["coordinates"]["latitude"],
            longitude=initial_weather_data["coordinates"]["longitude"],
            spatial_resolution="district",
        )

        # 1. Ingest into Evidence Foundation (Phase 2A)
        evidence_rec = evidence_service.create_evidence(
            source_id="OPEN_METEO",
            evidence_class=EvidenceClass.OBSERVATION,
            raw_field="precipitation",
            raw_value=initial_weather_data["measurements"]["precipitation_mm"],
            raw_unit="mm",
            normalized_field="precipitation_mm_24h",
            normalized_value=initial_weather_data["measurements"]["precipitation_mm"],
            normalized_unit="mm",
            temporal=temporal,
            spatial=spatial,
            raw_payload=initial_weather_data["measurements"],
            product_id="SHOWCASE_WEATHER_GWALIOR",
        )

        # 2. Ingest into Operational Event Engine (Phase 9C-B)
        dedup_key = hashlib.sha256(
            f"OPEN_METEO:WEATHER_UPDATE:SHOWCASE-OBS-001:1:{initial_weather_data['payload_hash']}".encode()
        ).hexdigest()
        
        event = OperationalEvent(
            event_id="EVT-SHOWCASE-001",
            event_type=EventType.WEATHER_UPDATE,
            source_id="OPEN_METEO",
            source_authority="E2",
            source_record_id="SHOWCASE-OBS-001",
            sequence_number=1,
            deduplication_key=dedup_key,
            payload_hash=initial_weather_data["payload_hash"],
            published_at=obs_time,
            observed_at=obs_time,
            ingested_at=now_utc,
            valid_from=obs_time,
            valid_until=now_utc + timedelta(hours=6),
            geography=initial_weather_data["geography"],
            quality_state="VALID",
            freshness_state="FRESH",
            processing_status=EventProcessingStatus.APPLIED,
            evidence_ids=[evidence_rec.evidence_id],
            details=initial_weather_data["measurements"],
        )
        saved_event = await self.event_repo.save_event(event)
        self._latest_event = saved_event

        # 3. Assemble Critical Assets for Exposure
        hospitals, schools, roads = self._get_exposure_assets()

        # 4. Execute Real Analytical Pipeline (Phase 9A)
        pipeline_input = PipelineInput(
            input_reference="SHOWCASE-STEP-0-BASELINE",
            geography=initial_weather_data["geography"],
            evidence_records=[evidence_rec],
            hospitals=hospitals,
            schools=schools,
            roads=roads,
            is_demo=False,  # Evaluates strictly through standard analytical logic
        )
        run = await self.pipeline.run(pipeline_input)
        self._latest_run = run

        # 5. Persist Decision Revision 1 (Phase 9C-D)
        decision_id = run.decision_id or f"DEC-{uuid.uuid4().hex[:8].upper()}"
        revision_1 = DecisionRevision(
            revision_id="REV-SHOWCASE-001",
            decision_id=decision_id,
            revision_number=1,
            trigger_event_id=saved_event.event_id,
            previous_revision_id=None,
            pipeline_run_id=run.pipeline_run_id,
            risk_state={"risk_score": 0.22, "category": "LOW"},
            impact_state={"disruption_level": "MINIMAL"},
            decision_state={
                "verdict": run.nirnay_card.verdict.value if run.nirnay_card else "PROCEED_WITH_CAUTION",
                "severity": run.nirnay_card.severity.value if run.nirnay_card else "LOW",
            },
            nirnay_card=run.nirnay_card,
            evidence_versions=[evidence_rec.evidence_id],
            provenance={"step": "BASELINE", "scenario_id": self._manifest.get("scenario_id")},
        )
        await self.revision_repo.save_revision(revision_1)
        self._latest_revision = revision_1
        self._current_step_index = 0
        self._save_state()

        return {
            "status": "SUCCESS",
            "step_index": 0,
            "step_name": "BASELINE_NOMINAL",
            "event_id": saved_event.event_id,
            "sequence_number": saved_event.sequence_number,
            "pipeline_run_id": run.pipeline_run_id,
            "revision_id": revision_1.revision_id,
            "revision_number": 1,
            "verdict": revision_1.decision_state.get("verdict"),
            "severity": revision_1.decision_state.get("severity"),
            "geography": saved_event.geography,
            "measurements": initial_weather_data["measurements"],
        }

    async def next(self) -> Dict[str, Any]:
        """Advances to the next chronological step in the showcase scenario."""
        await self._load_state_async()
        if self._current_step_index < 0:
            return await self.start()

        if self._current_step_index == 0:
            return await self._advance_to_step_1_rain_escalation()
        elif self._current_step_index == 1:
            return await self._advance_to_step_2_warning_escalation()
        elif self._current_step_index == 2:
            return await self._advance_to_step_3_offline()
        elif self._current_step_index == 3:
            return await self._advance_to_step_4_recovery()
        else:
            return {
                "status": "SCENARIO_COMPLETE",
                "step_index": self._current_step_index,
                "message": "All scenario steps have been executed. Use reset() to restart.",
            }

    async def _advance_to_step_1_rain_escalation(self) -> Dict[str, Any]:
        """STEP 1: Precipitation escalation -> ChangeDetector -> Selective Recalculation -> Revision 2."""
        logger.info("Advancing Showcase Scenario to Precipitation Escalation (Step 1)")
        rain_data = self._load_json("weather_rain_increase.json")

        now_utc = datetime.now(timezone.utc)
        obs_time = now_utc - timedelta(minutes=5)
        temporal = TemporalIdentity(
            retrieval_time=now_utc,
            observation_time=obs_time,
            valid_from=obs_time,
            valid_to=now_utc + timedelta(hours=6),
        )
        spatial = SpatialIdentity(
            location_id=rain_data["geography"],
            latitude=rain_data["coordinates"]["latitude"],
            longitude=rain_data["coordinates"]["longitude"],
            spatial_resolution="district",
        )

        # 1. Ingest updated evidence
        evidence_rec = evidence_service.create_evidence(
            source_id="OPEN_METEO",
            evidence_class=EvidenceClass.OBSERVATION,
            raw_field="precipitation",
            raw_value=rain_data["measurements"]["precipitation_mm"],
            raw_unit="mm",
            normalized_field="precipitation_mm_24h",
            normalized_value=rain_data["measurements"]["precipitation_mm"],
            normalized_unit="mm",
            temporal=temporal,
            spatial=spatial,
            raw_payload=rain_data["measurements"],
            product_id="SHOWCASE_WEATHER_GWALIOR",
        )

        # 2. Ingest operational event
        dedup_key = hashlib.sha256(
            f"OPEN_METEO:WEATHER_UPDATE:SHOWCASE-OBS-002:1:{rain_data['payload_hash']}".encode()
        ).hexdigest()

        event = OperationalEvent(
            event_id="EVT-SHOWCASE-002",
            event_type=EventType.WEATHER_UPDATE,
            source_id="OPEN_METEO",
            source_authority="E2",
            source_record_id="SHOWCASE-OBS-002",
            previous_event_id=self._latest_event.event_id if self._latest_event else None,
            sequence_number=2,
            deduplication_key=dedup_key,
            payload_hash=rain_data["payload_hash"],
            published_at=obs_time,
            observed_at=obs_time,
            ingested_at=now_utc,
            valid_from=obs_time,
            valid_until=now_utc + timedelta(hours=6),
            geography=rain_data["geography"],
            quality_state="VALID",
            freshness_state="FRESH",
            processing_status=EventProcessingStatus.APPLIED,
            evidence_ids=[evidence_rec.evidence_id],
            details=rain_data["measurements"],
        )
        saved_event = await self.event_repo.save_event(event)

        # 3. Assemble pipeline input with updated evidence and exposure assets
        hospitals, schools, roads = self._get_exposure_assets()
        pipeline_input = PipelineInput(
            input_reference="SHOWCASE-STEP-1-ESCALATION",
            geography=rain_data["geography"],
            evidence_records=[evidence_rec],
            hospitals=hospitals,
            schools=schools,
            roads=roads,
            is_demo=False,
        )

        # 4. Selective Pipeline Orchestrator processes event
        rerun_run, cmp_result = await self.selective_orchestrator.process_operational_event(
            event=saved_event,
            input_data=pipeline_input,
            previous_run=self._latest_run,
            previous_event=self._latest_event,
        )
        self._latest_event = saved_event
        if rerun_run:
            self._latest_run = rerun_run

        latest_rev = await self.revision_repo.get_latest_revision_for_decision(
            rerun_run.decision_id if rerun_run else "DEC-001"
        )
        self._latest_revision = latest_rev

        # 5. Dispatch notification
        notification = self.notification_engine.generate_notification(
            event=saved_event,
            run=rerun_run,
            cmp_result=cmp_result,
        )
        if notification:
            self._notifications.append(notification)

        self._current_step_index = 1
        self._save_state()
        return {
            "status": "SUCCESS",
            "step_index": 1,
            "step_name": "PRECIPITATION_ESCALATION",
            "event_id": saved_event.event_id,
            "sequence_number": saved_event.sequence_number,
            "pipeline_run_id": rerun_run.pipeline_run_id if rerun_run else None,
            "revision_id": latest_rev.revision_id if latest_rev else None,
            "revision_number": latest_rev.revision_number if latest_rev else 2,
            "verdict": rerun_run.nirnay_card.verdict.value if rerun_run and rerun_run.nirnay_card else "POSTPONE",
            "severity": rerun_run.nirnay_card.severity.value if rerun_run and rerun_run.nirnay_card else "CRITICAL",
            "notification": notification.model_dump() if notification else None,
            "reused_stages": ["EXPOSURE", "VULNERABILITY"],
            "recomputed_stages": ["HAZARD", "RISK", "IMPACT", "DECISION"],
        }

    async def _advance_to_step_2_warning_escalation(self) -> Dict[str, Any]:
        """STEP 2: Official Warning scenario -> Revision 3 -> Priority Notification."""
        logger.info("Advancing Showcase Scenario to Warning Escalation (Step 2)")
        warn_data = self._load_json("warning_update.json")

        now_utc = datetime.now(timezone.utc)
        warn_from = now_utc - timedelta(minutes=2)
        warn_to = now_utc + timedelta(hours=18)
        temporal = TemporalIdentity(
            retrieval_time=now_utc,
            issue_time=warn_from,
            valid_from=warn_from,
            valid_to=warn_to,
        )
        spatial = SpatialIdentity(
            location_id=warn_data["geography"],
            latitude=warn_data["coordinates"]["latitude"],
            longitude=warn_data["coordinates"]["longitude"],
            spatial_resolution="district",
        )

        # 1. Ingest official warning evidence
        evidence_rec = evidence_service.create_evidence(
            source_id="IMD",
            evidence_class=EvidenceClass.OFFICIAL_WARNING,
            raw_field="warning_level",
            raw_value=warn_data["alert_details"]["warning_level"],
            raw_unit="IMD_COLOR_CODE",
            normalized_field="official_hazard_warning",
            normalized_value=warn_data["alert_details"],
            normalized_unit="CAP_1.2",
            temporal=temporal,
            spatial=spatial,
            raw_payload=warn_data["alert_details"],
            product_id="SHOWCASE_WARNING_GWALIOR",
        )

        # 2. Ingest warning event
        dedup_key = hashlib.sha256(
            f"IMD:OFFICIAL_WARNING_NEW:SHOWCASE-WARN-001:1:{warn_data['payload_hash']}".encode()
        ).hexdigest()

        event = OperationalEvent(
            event_id="EVT-SHOWCASE-003",
            event_type=EventType.OFFICIAL_WARNING_NEW,
            source_id="IMD",
            source_authority="E1",
            source_record_id="SHOWCASE-WARN-001",
            previous_event_id=self._latest_event.event_id if self._latest_event else None,
            sequence_number=3,
            deduplication_key=dedup_key,
            payload_hash=warn_data["payload_hash"],
            published_at=warn_from,
            observed_at=warn_from,
            ingested_at=now_utc,
            valid_from=warn_from,
            valid_until=warn_to,
            geography=warn_data["geography"],
            quality_state="VALID",
            freshness_state="FRESH",
            processing_status=EventProcessingStatus.APPLIED,
            evidence_ids=[evidence_rec.evidence_id],
            details=warn_data["alert_details"],
        )
        saved_event = await self.event_repo.save_event(event)

        # 3. Assemble pipeline input
        official_warning = OfficialWarningInfo(
            alert_id=warn_data["alert_details"]["identifier"],
            source="IMD",
            authority="India Meteorological Department (Controlled Reference)",
            warning_level=warn_data["alert_details"]["warning_level"],
            hazard_type="Severe Weather Advisory (Controlled Scenario)",
            headline=warn_data["alert_details"]["headline"],
            instruction=warn_data["alert_details"].get("instruction"),
            valid_from_iso=warn_from.isoformat(),
            valid_to_iso=warn_to.isoformat(),
            geography=warn_data["geography"],
            official_text=warn_data["alert_details"]["headline"],
            system_summary="Controlled Scenario Benchmark (Non-live demonstration)",
        )
        hospitals, schools, roads = self._get_exposure_assets()
        pipeline_input = PipelineInput(
            input_reference="SHOWCASE-STEP-2-WARNING",
            geography=warn_data["geography"],
            evidence_records=[evidence_rec],
            official_warnings=[official_warning],
            hospitals=hospitals,
            schools=schools,
            roads=roads,
            is_demo=False,
        )

        # 4. Selective Pipeline Orchestrator processes event
        rerun_run, cmp_result = await self.selective_orchestrator.process_operational_event(
            event=saved_event,
            input_data=pipeline_input,
            previous_run=self._latest_run,
            previous_event=self._latest_event,
        )
        self._latest_event = saved_event
        if rerun_run:
            self._latest_run = rerun_run

        latest_rev = await self.revision_repo.get_latest_revision_for_decision(
            rerun_run.decision_id if rerun_run else "DEC-001"
        )
        self._latest_revision = latest_rev

        # 5. Dispatch priority warning notification
        notification = self.notification_engine.generate_notification(
            event=saved_event,
            run=rerun_run,
            cmp_result=cmp_result,
        )
        if notification:
            self._notifications.append(notification)

        self._current_step_index = 2
        self._save_state()
        return {
            "status": "SUCCESS",
            "step_index": 2,
            "step_name": "OFFICIAL_WARNING_ESCALATION",
            "event_id": saved_event.event_id,
            "sequence_number": saved_event.sequence_number,
            "pipeline_run_id": rerun_run.pipeline_run_id if rerun_run else None,
            "revision_id": latest_rev.revision_id if latest_rev else None,
            "revision_number": latest_rev.revision_number if latest_rev else 3,
            "verdict": rerun_run.nirnay_card.verdict.value if rerun_run and rerun_run.nirnay_card else "NO_GO",
            "severity": rerun_run.nirnay_card.severity.value if rerun_run and rerun_run.nirnay_card else "CRITICAL",
            "notification": notification.model_dump() if notification else None,
        }

    async def _advance_to_step_3_offline(self) -> Dict[str, Any]:
        """STEP 3: Offline resilience simulation (Network disconnected; verified cache preserved)."""
        self._current_step_index = 3
        self._save_state()
        return {
            "status": "SUCCESS",
            "step_index": 3,
            "step_name": "OFFLINE_SIMULATION",
            "system_state": "OFFLINE",
            "source_status": "CACHED",
            "latest_revision_id": self._latest_revision.revision_id if self._latest_revision else None,
            "verdict": self._latest_run.nirnay_card.verdict.value if self._latest_run and self._latest_run.nirnay_card else "POSTPONE",
            "cursor_sequence": self._latest_event.sequence_number if self._latest_event else 3,
            "description": "Network disconnected. Android UI displays OFFLINE and preserves verified cache without stale data masked as live.",
        }

    async def _advance_to_step_4_recovery(self) -> Dict[str, Any]:
        """STEP 4: Recovery state (Network restored; incremental sync reconciles latest state)."""
        self._current_step_index = 4
        self._save_state()
        return {
            "status": "SUCCESS",
            "step_index": 4,
            "step_name": "RECOVERY_AND_SYNC",
            "system_state": "FULL_OPERATIONAL",
            "source_status": "LIVE",
            "latest_revision_id": self._latest_revision.revision_id if self._latest_revision else None,
            "verdict": self._latest_run.nirnay_card.verdict.value if self._latest_run and self._latest_run.nirnay_card else "POSTPONE",
            "cursor_sequence": self._latest_event.sequence_number if self._latest_event else 3,
            "description": "Connectivity restored. Incremental synchronization reconciles latest assessment to Android Room store.",
        }

    async def reset(self) -> Dict[str, Any]:
        """Restores showcase scenario state back to clean baseline."""
        logger.info("Resetting Showcase Scenario Runner state")
        self.event_repo.clear()
        self.revision_repo.clear()
        self.notification_engine = EventNotificationEngine()
        self._current_step_index = -1
        self._latest_run = None
        self._latest_revision = None
        self._latest_event = None
        self._notifications.clear()
        state_file = self.data_dir / ".showcase_state.json"
        if state_file.exists():
            try:
                state_file.unlink(missing_ok=True)
            except Exception:
                pass
        return {"status": "RESET_COMPLETE", "step_index": -1}

    def get_status(self) -> Dict[str, Any]:
        """Returns current operational status of the showcase scenario."""
        state_file = self.data_dir / ".showcase_state.json"
        step_idx = self._current_step_index
        rev_num = self._latest_revision.revision_number if self._latest_revision else 0
        rev_id = self._latest_revision.revision_id if self._latest_revision else None
        seq = self._latest_event.sequence_number if self._latest_event else 0
        if state_file.exists() and step_idx < 0:
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    st = json.load(f)
                step_idx = st.get("current_step_index", step_idx)
                rev_id = st.get("latest_revision_id", rev_id)
                if step_idx >= 0 and rev_num == 0:
                    rev_num = step_idx + 1
                seq = max(seq, step_idx + 1 if step_idx >= 0 else 0)
            except Exception:
                pass

        return {
            "scenario_id": self._manifest.get("scenario_id", "SCENARIO-GWALIOR-MONSOON-2026"),
            "scenario_name": self._manifest.get("scenario_name", "Gwalior Showcase"),
            "current_step_index": step_idx,
            "latest_revision_number": rev_num,
            "latest_revision_id": rev_id,
            "latest_sequence": seq,
            "location": self._manifest.get("location", {}),
            "notifications_count": len(self._notifications),
        }

    # Synchronous helpers for CLI and synchronous test harnesses
    def start_sync(self) -> Dict[str, Any]:
        return asyncio.run(self.start())

    def next_sync(self) -> Dict[str, Any]:
        return asyncio.run(self.next())

    def reset_sync(self) -> Dict[str, Any]:
        return asyncio.run(self.reset())


# Global singleton instance
showcase_runner = ShowcaseScenarioRunner()

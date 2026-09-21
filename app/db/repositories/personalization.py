"""Repositories for Phase 10 personalization, decision history, actions, outcomes, and forecast verification."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.personalization import (
    DecisionHistoryRecord,
    DecisionOutcomeRecord,
    ForecastVerificationRecord,
    UserActionTrackingRecord,
    UserPreferencesRecord,
)
from app.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class UserPreferencesRepository(BaseRepository[UserPreferencesRecord]):
    """Async repository for user personalization preferences."""

    def __init__(self, session: AsyncSession):
        super().__init__(session=session, model=UserPreferencesRecord)

    async def get_preferences(self, user_id: str) -> Optional[UserPreferencesRecord]:
        """Retrieves preferences for a user if configured."""
        stmt = select(UserPreferencesRecord).where(UserPreferencesRecord.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def upsert_preferences(
        self,
        user_id: str,
        preferred_language: str = "en",
        min_severity: str = "low",
        proactive_enabled: bool = True,
        farmer_alerts_enabled: bool = True,
        official_warnings_only: bool = False,
        preferred_alert_categories: Optional[List[str]] = None,
        operation_priorities: Optional[List[str]] = None,
        preferred_notification_timing: str = "morning",
        preferred_units: Optional[Dict[str, str]] = None,
        explanation_detail: str = "standard",
        quiet_hours: Optional[Dict[str, int]] = None,
    ) -> UserPreferencesRecord:
        """Upserts user preferences record."""
        now_utc = datetime.now(timezone.utc)
        record = await self.get_preferences(user_id)
        if record:
            record.preferred_language = preferred_language
            record.min_severity = min_severity
            record.proactive_enabled = proactive_enabled
            record.farmer_alerts_enabled = farmer_alerts_enabled
            record.official_warnings_only = official_warnings_only
            if preferred_alert_categories is not None:
                record.preferred_alert_categories = preferred_alert_categories
            if operation_priorities is not None:
                record.operation_priorities = operation_priorities
            record.preferred_notification_timing = preferred_notification_timing
            if preferred_units is not None:
                record.preferred_units = preferred_units
            record.explanation_detail = explanation_detail
            record.quiet_hours = quiet_hours
            record.updated_at = now_utc
            await self.session.commit()
            await self.session.refresh(record)
            return record

        record = UserPreferencesRecord(
            user_id=user_id,
            preferred_language=preferred_language,
            min_severity=min_severity,
            proactive_enabled=proactive_enabled,
            farmer_alerts_enabled=farmer_alerts_enabled,
            official_warnings_only=official_warnings_only,
            preferred_alert_categories=preferred_alert_categories or ["rainfall", "wind", "heat", "pest"],
            operation_priorities=operation_priorities or ["spraying", "irrigation", "harvesting"],
            preferred_notification_timing=preferred_notification_timing,
            preferred_units=preferred_units or {"temperature": "celsius", "wind": "kmh", "rain": "mm"},
            explanation_detail=explanation_detail,
            quiet_hours=quiet_hours,
            created_at=now_utc,
            updated_at=now_utc,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record


class DecisionHistoryRepository(BaseRepository[DecisionHistoryRecord]):
    """Async repository for immutable historical decisions."""

    def __init__(self, session: AsyncSession):
        super().__init__(session=session, model=DecisionHistoryRecord)

    async def record_decision(
        self,
        decision_id: str,
        user_id: str,
        question: str,
        verdict: str,
        severity: str,
        recommended_action: str,
        location: Dict[str, Any],
        evidence_snapshot: Dict[str, Any],
        uncertainty: Dict[str, Any],
        provenance: Dict[str, Any],
        event_id: Optional[str] = None,
        plot_id: Optional[str] = None,
        operation: Optional[str] = None,
        action_window: Optional[Dict[str, Any]] = None,
        official_alert_id: Optional[str] = None,
        official_warning_level: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> DecisionHistoryRecord:
        """Records an immutable historical decision."""
        record = DecisionHistoryRecord(
            history_id=f"hist_{uuid.uuid4().hex[:12]}",
            decision_id=decision_id,
            event_id=event_id,
            user_id=user_id,
            plot_id=plot_id,
            timestamp=timestamp or datetime.now(timezone.utc),
            question=question,
            verdict=verdict,
            severity=severity,
            recommended_action=recommended_action,
            location=location,
            operation=operation,
            evidence_snapshot=evidence_snapshot,
            uncertainty=uncertainty,
            provenance=provenance,
            action_window=action_window,
            official_alert_id=official_alert_id,
            official_warning_level=official_warning_level,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_user_history(
        self,
        user_id: str,
        limit: int = 50,
    ) -> List[DecisionHistoryRecord]:
        """Fetches auditable decision history for a user sorted latest first."""
        stmt = (
            select(DecisionHistoryRecord)
            .where(DecisionHistoryRecord.user_id == user_id)
            .order_by(desc(DecisionHistoryRecord.timestamp))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_decision_id(self, decision_id: str) -> Optional[DecisionHistoryRecord]:
        """Fetches a specific historical decision."""
        stmt = select(DecisionHistoryRecord).where(DecisionHistoryRecord.decision_id == decision_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()


class UserActionRepository(BaseRepository[UserActionTrackingRecord]):
    """Async repository for tracking user interactions with decisions and events."""

    def __init__(self, session: AsyncSession):
        super().__init__(session=session, model=UserActionTrackingRecord)

    async def record_action(
        self,
        user_id: str,
        action_type: str,
        decision_id: Optional[str] = None,
        event_id: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> UserActionTrackingRecord:
        """Records an explicit user action."""
        record = UserActionTrackingRecord(
            action_id=f"act_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            decision_id=decision_id,
            event_id=event_id,
            action_type=action_type,
            timestamp=timestamp or datetime.now(timezone.utc),
            metadata_json=metadata_json or {},
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_actions_for_user(self, user_id: str, limit: int = 100) -> List[UserActionTrackingRecord]:
        """Retrieves actions performed by a user."""
        stmt = (
            select(UserActionTrackingRecord)
            .where(UserActionTrackingRecord.user_id == user_id)
            .order_by(desc(UserActionTrackingRecord.timestamp))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_actions_for_decision(self, decision_id: str) -> List[UserActionTrackingRecord]:
        """Retrieves actions associated with a specific decision."""
        stmt = (
            select(UserActionTrackingRecord)
            .where(UserActionTrackingRecord.decision_id == decision_id)
            .order_by(desc(UserActionTrackingRecord.timestamp))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class DecisionOutcomeRepository(BaseRepository[DecisionOutcomeRecord]):
    """Async repository for reported agricultural and alert outcomes."""

    def __init__(self, session: AsyncSession):
        super().__init__(session=session, model=DecisionOutcomeRecord)

    async def record_outcome(
        self,
        user_id: str,
        outcome_type: str,
        decision_id: Optional[str] = None,
        event_id: Optional[str] = None,
        notes: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
        reported_at: Optional[datetime] = None,
    ) -> DecisionOutcomeRecord:
        """Records an explicit user-reported outcome."""
        record = DecisionOutcomeRecord(
            outcome_id=f"outc_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            decision_id=decision_id,
            event_id=event_id,
            outcome_type=outcome_type,
            reported_at=reported_at or datetime.now(timezone.utc),
            notes=notes,
            metadata_json=metadata_json or {},
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_outcomes_for_user(self, user_id: str, limit: int = 100) -> List[DecisionOutcomeRecord]:
        """Retrieves outcomes reported by a user."""
        stmt = (
            select(DecisionOutcomeRecord)
            .where(DecisionOutcomeRecord.user_id == user_id)
            .order_by(desc(DecisionOutcomeRecord.reported_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ForecastVerificationRepository(BaseRepository[ForecastVerificationRecord]):
    """Async repository for forecast vs observation verification pairs."""

    def __init__(self, session: AsyncSession):
        super().__init__(session=session, model=ForecastVerificationRecord)

    async def record_verification(
        self,
        location_name: str,
        latitude: float,
        longitude: float,
        forecast_time: datetime,
        observation_time: datetime,
        forecast_temp_c: Optional[float] = None,
        observed_temp_c: Optional[float] = None,
        temp_error_c: Optional[float] = None,
        forecast_rain_mm: Optional[float] = None,
        observed_rain_mm: Optional[float] = None,
        rain_error_mm: Optional[float] = None,
        rain_hit_miss: Optional[str] = None,
        forecast_wind_kmh: Optional[float] = None,
        observed_wind_kmh: Optional[float] = None,
        wind_error_kmh: Optional[float] = None,
        verification_status: str = "verified",
    ) -> ForecastVerificationRecord:
        """Records a paired forecast vs observation verification entry."""
        record = ForecastVerificationRecord(
            verification_id=f"verif_{uuid.uuid4().hex[:12]}",
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            forecast_time=forecast_time,
            observation_time=observation_time,
            forecast_temp_c=forecast_temp_c,
            observed_temp_c=observed_temp_c,
            temp_error_c=temp_error_c,
            forecast_rain_mm=forecast_rain_mm,
            observed_rain_mm=observed_rain_mm,
            rain_error_mm=rain_error_mm,
            rain_hit_miss=rain_hit_miss,
            forecast_wind_kmh=forecast_wind_kmh,
            observed_wind_kmh=observed_wind_kmh,
            wind_error_kmh=wind_error_kmh,
            verification_status=verification_status,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_verifications_for_location(
        self,
        latitude: float,
        longitude: float,
        limit: int = 100,
    ) -> List[ForecastVerificationRecord]:
        """Retrieves verification pairs for a coordinate location."""
        stmt = (
            select(ForecastVerificationRecord)
            .where(
                ForecastVerificationRecord.latitude == latitude,
                ForecastVerificationRecord.longitude == longitude,
            )
            .order_by(desc(ForecastVerificationRecord.observation_time))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

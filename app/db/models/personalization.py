"""Persistent ORM models for Phase 10: Personalization, Decision Quality & History.

Provides durable PostgreSQL tables for:
1. UserPreferencesRecord (user_preferences_store): Persistent user configuration.
2. DecisionHistoryRecord (decision_history): Immutable, auditable decision history.
3. UserActionTrackingRecord (user_action_tracking): User interactions with decisions/events.
4. DecisionOutcomeRecord (decision_outcomes): Explicit reported outcomes.
5. ForecastVerificationRecord (forecast_verifications): Paired forecast vs observation quality records.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserPreferencesRecord(Base):
    """Persistent storage for farmer/user personalization and notification preferences."""

    __tablename__ = "user_preferences_store"

    user_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
        comment="User identifier owning these preferences",
    )
    preferred_language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="en",
        comment="Preferred language code (en, hi, mr, gu, bn)",
    )
    min_severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="low",
        comment="Minimum severity threshold to trigger push/advisories",
    )
    proactive_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Master toggle for proactive recommendations",
    )
    farmer_alerts_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Enable agricultural operation events",
    )
    official_warnings_only: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Suppress non-official advisory events",
    )
    preferred_alert_categories: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: ["rainfall", "wind", "heat", "pest"],
        comment="List of alert categories prioritized by user",
    )
    operation_priorities: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: ["spraying", "irrigation", "harvesting"],
        comment="List of agricultural operations ranked by farmer preference",
    )
    preferred_notification_timing: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="morning",
        comment="Timing preference: morning, evening, immediate",
    )
    preferred_units: Mapped[Dict[str, str]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: {"temperature": "celsius", "wind": "kmh", "rain": "mm"},
        comment="Preferred units dictionary",
    )
    explanation_detail: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="standard",
        comment="Explanation detail preference: concise, standard, detailed",
    )
    quiet_hours: Mapped[Optional[Dict[str, int]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Quiet hours dictionary, e.g. {'start_hour': 22, 'end_hour': 6}",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<UserPreferencesRecord(user={self.user_id!r}, lang={self.preferred_language!r})>"


class DecisionHistoryRecord(Base):
    """Immutable, audit-grade historical decision and proactive event log."""

    __tablename__ = "decision_history"

    history_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for the historical decision entry",
    )
    decision_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Deterministic decision audit ID or generated ID",
    )
    event_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Associated proactive event ID if emitted via proactive engine",
    )
    user_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Target farmer or user identifier",
    )
    plot_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Referenced farmer plot ID",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        comment="Decision evaluation timestamp",
    )
    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Original user operational question or event trigger query",
    )
    verdict: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Authoritative verdict (GO, NO_GO, POSTPONE, PROCEED_WITH_CAUTION)",
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Decision severity (critical, high, moderate, low, info)",
    )
    recommended_action: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Unambiguous operational command text",
    )
    location: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Location metadata (name, lat, lon, district, state)",
    )
    operation: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Operational context (e.g. spraying, irrigation, harvest)",
    )
    evidence_snapshot: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Frozen snapshot of weather variables and threshold checks",
    )
    uncertainty: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Disclosed forecast limitations and model uncertainty",
    )
    provenance: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Verified provider citations, models, and timestamps",
    )
    action_window: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Calculated operational timing window if available",
    )
    official_alert_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Linked official CAP alert ID if applicable",
    )
    official_warning_level: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Official warning level (Green, Yellow, Orange, Red)",
    )

    __table_args__ = (
        Index("ix_decision_history_user_time", "user_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<DecisionHistoryRecord(id={self.history_id!r}, decision={self.decision_id!r}, verdict={self.verdict!r})>"


class UserActionTrackingRecord(Base):
    """Auditable log of explicit user actions taken on decisions/events."""

    __tablename__ = "user_action_tracking"

    action_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for the action entry",
    )
    user_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="User who performed the action",
    )
    decision_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Associated decision ID if applicable",
    )
    event_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Associated proactive event ID if applicable",
    )
    action_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
        comment="Action: viewed, acknowledged, dismissed, followed, postponed, marked_completed, ignored",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Additional context (client platform, session ID, notes)",
    )

    __table_args__ = (
        Index("ix_user_actions_user_decision", "user_id", "decision_id"),
        Index("ix_user_actions_user_event", "user_id", "event_id"),
    )

    def __repr__(self) -> str:
        return f"<UserActionTrackingRecord(id={self.action_id!r}, user={self.user_id!r}, action={self.action_type!r})>"


class DecisionOutcomeRecord(Base):
    """Explicit reported outcomes for agricultural operations and alerts."""

    __tablename__ = "decision_outcomes"

    outcome_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for outcome record",
    )
    user_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="User who reported the outcome",
    )
    decision_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Referenced decision ID",
    )
    event_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Referenced proactive event ID",
    )
    outcome_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Classified outcome (e.g. spraying_completed, spraying_postponed)",
    )
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="User feedback or field notes",
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Contextual metadata",
    )

    __table_args__ = (
        Index("ix_outcomes_user_decision", "user_id", "decision_id"),
        Index("ix_outcomes_user_event", "user_id", "event_id"),
    )

    def __repr__(self) -> str:
        return f"<DecisionOutcomeRecord(id={self.outcome_id!r}, outcome={self.outcome_type!r})>"


class ForecastVerificationRecord(Base):
    """Paired evaluation comparing deterministic forecasts against later verified observations."""

    __tablename__ = "forecast_verifications"

    verification_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique verification pair identifier",
    )
    location_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Geographic location name",
    )
    latitude: Mapped[float] = mapped_column(
        Numeric(8, 5),
        nullable=False,
        comment="Latitude (WGS84)",
    )
    longitude: Mapped[float] = mapped_column(
        Numeric(8, 5),
        nullable=False,
        comment="Longitude (WGS84)",
    )
    forecast_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Timestamp when forecast was produced or issued",
    )
    observation_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Timestamp of verified real observation",
    )
    forecast_temp_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    observed_temp_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temp_error_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    forecast_rain_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    observed_rain_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rain_error_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rain_hit_miss: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    
    forecast_wind_kmh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    observed_wind_kmh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wind_error_kmh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    verification_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="verified",
        comment="Status: verified, unavailable",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_verifications_loc_time", "latitude", "longitude", "observation_time"),
    )

    def __repr__(self) -> str:
        return f"<ForecastVerificationRecord(id={self.verification_id!r}, loc={self.location_name!r}, status={self.verification_status!r})>"

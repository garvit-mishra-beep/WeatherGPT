"""Persistent models for proactive notification outbox and device tokens (Phase 9).

Provides durable storage for:
1. ProactiveNotificationOutbox: Decoupled delivery outbox ensuring events survive
   network drops, worker restarts, and FCM throttling.
2. UserDeviceToken: Device push tokens mapped to user identities with active lifecycle.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProactiveNotificationOutbox(Base):
    """Durable notification outbox record storing pending, delivered, or failed push dispatches."""

    __tablename__ = "proactive_notification_outbox"

    outbox_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for the outbox delivery item",
    )
    event_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Traceable ID of the parent WeatherDecisionEvent",
    )
    user_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Recipient user or farmer identifier",
    )
    plot_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Associated farmer plot ID if applicable",
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Decision event type (e.g. OFFICIAL_ALERT, SPRAY_WINDOW_CHANGE)",
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Event severity (CRITICAL, HIGH, MODERATE, LOW, INFO)",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Concise notification title",
    )
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Direct recommended operational action text",
    )
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Full serialized WeatherDecisionEvent payload for client rendering",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Timestamp when event was enqueued into outbox",
    )
    valid_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Operational validity expiration timestamp",
    )
    delivery_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="Delivery lifecycle: pending, delivered, failed, expired, suppressed",
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total dispatch attempts performed by worker",
    )
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of most recent delivery attempt",
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when push transport confirmed delivery",
    )
    error_info: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Diagnostic error details from transport failure (secrets masked)",
    )
    dedup_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA-256 deduplication key for delivery idempotency",
    )

    def __repr__(self) -> str:
        return f"<ProactiveNotificationOutbox(id={self.outbox_id!r}, event={self.event_id!r}, status={self.delivery_status!r})>"


class UserDeviceToken(Base):
    """Registered user device with active FCM token for push notifications."""

    __tablename__ = "user_device_tokens"

    device_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
        comment="Unique client hardware or install identifier",
    )
    user_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="User owning this device registration",
    )
    fcm_token: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
        comment="Active Firebase Cloud Messaging registration token",
    )
    platform: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="android",
        comment="Device OS platform (android, ios, web)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="True if token is valid and active; False if unregistered/expired",
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

    __table_args__ = (
        UniqueConstraint("user_id", "device_id", name="uq_user_device"),
    )

    def __repr__(self) -> str:
        return f"<UserDeviceToken(device={self.device_id!r}, user={self.user_id!r}, active={self.is_active!r})>"

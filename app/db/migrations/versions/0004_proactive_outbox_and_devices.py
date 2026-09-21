"""Add proactive notification outbox and user device tokens tables (Phase 9)

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-09 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Proactive Notification Outbox table
    op.create_table(
        'proactive_notification_outbox',
        sa.Column('outbox_id', sa.String(length=36), nullable=False, comment='Unique identifier for the outbox delivery item'),
        sa.Column('event_id', sa.String(length=50), nullable=False, comment='Traceable ID of the parent WeatherDecisionEvent'),
        sa.Column('user_id', sa.String(length=100), nullable=False, comment='Recipient user or farmer identifier'),
        sa.Column('plot_id', sa.String(length=50), nullable=True, comment='Associated farmer plot ID if applicable'),
        sa.Column('event_type', sa.String(length=50), nullable=False, comment='Decision event type'),
        sa.Column('severity', sa.String(length=20), nullable=False, comment='Event severity'),
        sa.Column('title', sa.String(length=255), nullable=False, comment='Concise notification title'),
        sa.Column('body', sa.Text(), nullable=False, comment='Direct recommended operational action text'),
        sa.Column('payload', sa.JSON(), nullable=False, comment='Full serialized WeatherDecisionEvent payload'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='Timestamp when event was enqueued into outbox'),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True, comment='Operational validity expiration timestamp'),
        sa.Column('delivery_status', sa.String(length=20), nullable=False, server_default='pending', comment='Delivery lifecycle status'),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0', comment='Total dispatch attempts performed by worker'),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp of most recent delivery attempt'),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when push transport confirmed delivery'),
        sa.Column('error_info', sa.Text(), nullable=True, comment='Diagnostic error details from transport failure'),
        sa.Column('dedup_key', sa.String(length=64), nullable=False, comment='SHA-256 deduplication key for delivery idempotency'),
        sa.PrimaryKeyConstraint('outbox_id'),
    )
    op.create_index(op.f('ix_proactive_outbox_event_id'), 'proactive_notification_outbox', ['event_id'], unique=False)
    op.create_index(op.f('ix_proactive_outbox_user_id'), 'proactive_notification_outbox', ['user_id'], unique=False)
    op.create_index(op.f('ix_proactive_outbox_status'), 'proactive_notification_outbox', ['delivery_status'], unique=False)
    op.create_index(op.f('ix_proactive_outbox_dedup_key'), 'proactive_notification_outbox', ['dedup_key'], unique=False)

    # 2. User Device Tokens table
    op.create_table(
        'user_device_tokens',
        sa.Column('device_id', sa.String(length=100), nullable=False, comment='Unique client hardware or install identifier'),
        sa.Column('user_id', sa.String(length=100), nullable=False, comment='User owning this device registration'),
        sa.Column('fcm_token', sa.String(length=500), nullable=False, comment='Active Firebase Cloud Messaging registration token'),
        sa.Column('platform', sa.String(length=20), nullable=False, server_default='android', comment='Device OS platform'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true(), comment='True if token is active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('device_id'),
        sa.UniqueConstraint('user_id', 'device_id', name='uq_user_device'),
    )
    op.create_index(op.f('ix_user_device_tokens_user_id'), 'user_device_tokens', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_device_tokens_fcm_token'), 'user_device_tokens', ['fcm_token'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_device_tokens_fcm_token'), table_name='user_device_tokens')
    op.drop_index(op.f('ix_user_device_tokens_user_id'), table_name='user_device_tokens')
    op.drop_table('user_device_tokens')

    op.drop_index(op.f('ix_proactive_outbox_dedup_key'), table_name='proactive_notification_outbox')
    op.drop_index(op.f('ix_proactive_outbox_status'), table_name='proactive_notification_outbox')
    op.drop_index(op.f('ix_proactive_outbox_user_id'), table_name='proactive_notification_outbox')
    op.drop_index(op.f('ix_proactive_outbox_event_id'), table_name='proactive_notification_outbox')
    op.drop_table('proactive_notification_outbox')

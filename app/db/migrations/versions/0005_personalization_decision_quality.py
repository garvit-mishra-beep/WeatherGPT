"""Add personalization, decision history, actions, outcomes, and forecast verification tables (Phase 10)

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-09 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. User Preferences Store
    op.create_table(
        'user_preferences_store',
        sa.Column('user_id', sa.String(length=100), nullable=False, comment='User identifier'),
        sa.Column('preferred_language', sa.String(length=10), nullable=False, server_default='en'),
        sa.Column('min_severity', sa.String(length=20), nullable=False, server_default='low'),
        sa.Column('proactive_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('farmer_alerts_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('official_warnings_only', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('preferred_alert_categories', sa.JSON(), nullable=False),
        sa.Column('operation_priorities', sa.JSON(), nullable=False),
        sa.Column('preferred_notification_timing', sa.String(length=20), nullable=False, server_default='morning'),
        sa.Column('preferred_units', sa.JSON(), nullable=False),
        sa.Column('explanation_detail', sa.String(length=20), nullable=False, server_default='standard'),
        sa.Column('quiet_hours', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('user_id'),
    )

    # 2. Decision History Table
    op.create_table(
        'decision_history',
        sa.Column('history_id', sa.String(length=36), nullable=False),
        sa.Column('decision_id', sa.String(length=50), nullable=False),
        sa.Column('event_id', sa.String(length=50), nullable=True),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('plot_id', sa.String(length=50), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('verdict', sa.String(length=30), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('recommended_action', sa.Text(), nullable=False),
        sa.Column('location', sa.JSON(), nullable=False),
        sa.Column('operation', sa.String(length=50), nullable=True),
        sa.Column('evidence_snapshot', sa.JSON(), nullable=False),
        sa.Column('uncertainty', sa.JSON(), nullable=False),
        sa.Column('provenance', sa.JSON(), nullable=False),
        sa.Column('action_window', sa.JSON(), nullable=True),
        sa.Column('official_alert_id', sa.String(length=100), nullable=True),
        sa.Column('official_warning_level', sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint('history_id'),
    )
    op.create_index(op.f('ix_decision_history_decision_id'), 'decision_history', ['decision_id'], unique=False)
    op.create_index(op.f('ix_decision_history_event_id'), 'decision_history', ['event_id'], unique=False)
    op.create_index(op.f('ix_decision_history_user_id'), 'decision_history', ['user_id'], unique=False)
    op.create_index(op.f('ix_decision_history_plot_id'), 'decision_history', ['plot_id'], unique=False)
    op.create_index(op.f('ix_decision_history_timestamp'), 'decision_history', ['timestamp'], unique=False)
    op.create_index('ix_decision_history_user_time', 'decision_history', ['user_id', 'timestamp'], unique=False)

    # 3. User Action Tracking Table
    op.create_table(
        'user_action_tracking',
        sa.Column('action_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('decision_id', sa.String(length=50), nullable=True),
        sa.Column('event_id', sa.String(length=50), nullable=True),
        sa.Column('action_type', sa.String(length=30), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('action_id'),
    )
    op.create_index(op.f('ix_user_action_tracking_user_id'), 'user_action_tracking', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_action_tracking_decision_id'), 'user_action_tracking', ['decision_id'], unique=False)
    op.create_index(op.f('ix_user_action_tracking_event_id'), 'user_action_tracking', ['event_id'], unique=False)
    op.create_index(op.f('ix_user_action_tracking_action_type'), 'user_action_tracking', ['action_type'], unique=False)
    op.create_index('ix_user_actions_user_decision', 'user_action_tracking', ['user_id', 'decision_id'], unique=False)
    op.create_index('ix_user_actions_user_event', 'user_action_tracking', ['user_id', 'event_id'], unique=False)

    # 4. Decision Outcomes Table
    op.create_table(
        'decision_outcomes',
        sa.Column('outcome_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('decision_id', sa.String(length=50), nullable=True),
        sa.Column('event_id', sa.String(length=50), nullable=True),
        sa.Column('outcome_type', sa.String(length=50), nullable=False),
        sa.Column('reported_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('outcome_id'),
    )
    op.create_index(op.f('ix_decision_outcomes_user_id'), 'decision_outcomes', ['user_id'], unique=False)
    op.create_index(op.f('ix_decision_outcomes_decision_id'), 'decision_outcomes', ['decision_id'], unique=False)
    op.create_index(op.f('ix_decision_outcomes_event_id'), 'decision_outcomes', ['event_id'], unique=False)
    op.create_index(op.f('ix_decision_outcomes_outcome_type'), 'decision_outcomes', ['outcome_type'], unique=False)
    op.create_index('ix_outcomes_user_decision', 'decision_outcomes', ['user_id', 'decision_id'], unique=False)
    op.create_index('ix_outcomes_user_event', 'decision_outcomes', ['user_id', 'event_id'], unique=False)

    # 5. Forecast Verifications Table
    op.create_table(
        'forecast_verifications',
        sa.Column('verification_id', sa.String(length=36), nullable=False),
        sa.Column('location_name', sa.String(length=100), nullable=False),
        sa.Column('latitude', sa.Numeric(precision=8, scale=5), nullable=False),
        sa.Column('longitude', sa.Numeric(precision=8, scale=5), nullable=False),
        sa.Column('forecast_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('observation_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('forecast_temp_c', sa.Float(), nullable=True),
        sa.Column('observed_temp_c', sa.Float(), nullable=True),
        sa.Column('temp_error_c', sa.Float(), nullable=True),
        sa.Column('forecast_rain_mm', sa.Float(), nullable=True),
        sa.Column('observed_rain_mm', sa.Float(), nullable=True),
        sa.Column('rain_error_mm', sa.Float(), nullable=True),
        sa.Column('rain_hit_miss', sa.String(length=30), nullable=True),
        sa.Column('forecast_wind_kmh', sa.Float(), nullable=True),
        sa.Column('observed_wind_kmh', sa.Float(), nullable=True),
        sa.Column('wind_error_kmh', sa.Float(), nullable=True),
        sa.Column('verification_status', sa.String(length=20), nullable=False, server_default='verified'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('verification_id'),
    )
    op.create_index('ix_verifications_loc_time', 'forecast_verifications', ['latitude', 'longitude', 'observation_time'], unique=False)


def downgrade() -> None:
    op.drop_table('forecast_verifications')
    op.drop_table('decision_outcomes')
    op.drop_table('user_action_tracking')
    op.drop_table('decision_history')
    op.drop_table('user_preferences_store')

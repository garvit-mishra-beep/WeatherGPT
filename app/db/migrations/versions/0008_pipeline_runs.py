"""Add Phase 9A Pipeline Runs table (pipeline_runs)

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-21 11:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0008'
down_revision: Union[str, None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pipeline_runs',
        sa.Column('pipeline_run_id', sa.String(length=64), nullable=False, comment='Canonical pipeline run ID'),
        sa.Column('pipeline_version', sa.String(length=16), nullable=False, server_default='1.0.0'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('input_type', sa.String(length=64), nullable=False, server_default='MULTI_HAZARD_ASSESSMENT'),
        sa.Column('input_reference', sa.String(length=128), nullable=False, server_default='DEFAULT'),
        sa.Column('input_hash', sa.String(length=64), nullable=False, comment='Idempotency input hash'),
        sa.Column('source_status', sa.String(length=32), nullable=False, server_default='LIVE'),
        sa.Column('pipeline_state', sa.String(length=32), nullable=False),
        sa.Column('current_stage', sa.String(length=32), nullable=True),
        sa.Column('failed_stage', sa.String(length=32), nullable=True),
        sa.Column('completed_stages', sa.JSON(), nullable=False),
        sa.Column('evidence_ids', sa.JSON(), nullable=False),
        sa.Column('hazard_evaluation_ids', sa.JSON(), nullable=False),
        sa.Column('exposure_evaluation_ids', sa.JSON(), nullable=False),
        sa.Column('vulnerability_evaluation_ids', sa.JSON(), nullable=False),
        sa.Column('risk_assessment_ids', sa.JSON(), nullable=False),
        sa.Column('impact_assessment_ids', sa.JSON(), nullable=False),
        sa.Column('decision_id', sa.String(length=64), nullable=True),
        sa.Column('quality_state', sa.String(length=32), nullable=False, server_default='VALID'),
        sa.Column('data_coverage', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('prototype_flags', sa.JSON(), nullable=False),
        sa.Column('provenance_id', sa.String(length=64), nullable=False),
        sa.Column('error_code', sa.String(length=64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('stage_executions', sa.JSON(), nullable=False),
        sa.Column('nirnay_card_payload', sa.JSON(), nullable=True),
        sa.Column('full_payload', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('pipeline_run_id'),
    )
    op.create_index('idx_pipeline_runs_state', 'pipeline_runs', ['pipeline_state'])
    op.create_index('idx_pipeline_runs_started', 'pipeline_runs', ['started_at'])
    op.create_index('idx_pipeline_runs_input_hash', 'pipeline_runs', ['input_hash'])
    op.create_index('idx_pipeline_runs_provenance', 'pipeline_runs', ['provenance_id'])


def downgrade() -> None:
    op.drop_index('idx_pipeline_runs_provenance', table_name='pipeline_runs')
    op.drop_index('idx_pipeline_runs_input_hash', table_name='pipeline_runs')
    op.drop_index('idx_pipeline_runs_started', table_name='pipeline_runs')
    op.drop_index('idx_pipeline_runs_state', table_name='pipeline_runs')
    op.drop_table('pipeline_runs')

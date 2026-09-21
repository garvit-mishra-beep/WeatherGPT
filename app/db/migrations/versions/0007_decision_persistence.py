"""Add Phase 8 Decision Support tables (decision_assessments, decision_history, decision_verifications)

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-20 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0007'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Decision Assessments
    op.create_table(
        'decision_assessments',
        sa.Column('decision_id', sa.String(length=50), nullable=False, comment='Unique decision execution identifier'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1', comment='Decision version sequence'),
        sa.Column('assessment_time', sa.DateTime(timezone=True), nullable=False, comment='Evaluation ISO timestamp'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, comment='Decision validity expiration timestamp'),
        sa.Column('hazard_evaluation_id', sa.String(length=50), nullable=True),
        sa.Column('exposure_id', sa.String(length=50), nullable=True),
        sa.Column('vulnerability_id', sa.String(length=50), nullable=True),
        sa.Column('risk_id', sa.String(length=50), nullable=True),
        sa.Column('impact_id', sa.String(length=50), nullable=True),
        sa.Column('decision_state', sa.String(length=50), nullable=False),
        sa.Column('priority_class', sa.String(length=50), nullable=False),
        sa.Column('decision_conditions', sa.JSON(), nullable=False),
        sa.Column('eligible_actions', sa.JSON(), nullable=False),
        sa.Column('prohibited_actions', sa.JSON(), nullable=False),
        sa.Column('official_warning_ids', sa.JSON(), nullable=False),
        sa.Column('method_ids', sa.JSON(), nullable=False),
        sa.Column('rule_ids', sa.JSON(), nullable=False),
        sa.Column('claim_ids', sa.JSON(), nullable=False),
        sa.Column('evidence_quality', sa.String(length=50), nullable=False, server_default='VALID'),
        sa.Column('data_coverage', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('staleness_state', sa.String(length=50), nullable=False, server_default='FRESH'),
        sa.Column('human_verification_required', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('verification_status', sa.String(length=50), nullable=False, server_default='NOT_REQUIRED'),
        sa.Column('provenance_id', sa.String(length=64), nullable=False),
        sa.Column('package_payload', sa.JSON(), nullable=True, comment='Full serialized DecisionPackage snapshot'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('decision_id'),
    )
    op.create_index('idx_decision_assessment_created_at', 'decision_assessments', ['created_at'])
    op.create_index('idx_decision_assessment_version', 'decision_assessments', ['version'])
    op.create_index('idx_decision_assessment_expires_at', 'decision_assessments', ['expires_at'])
    op.create_index('idx_decision_assessment_hazard_eval_id', 'decision_assessments', ['hazard_evaluation_id'])
    op.create_index('idx_decision_assessment_state', 'decision_assessments', ['decision_state'])

    # 2. Decision History (State Transitions)
    op.create_table(
        'decision_transition_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('decision_id', sa.String(length=64), nullable=False),
        sa.Column('previous_decision_id', sa.String(length=64), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('previous_state', sa.String(length=32), nullable=True),
        sa.Column('new_state', sa.String(length=32), nullable=False),
        sa.Column('change_reason', sa.String(length=64), nullable=False),
        sa.Column('changed_fields', sa.JSON(), nullable=True),
        sa.Column('rule_id', sa.String(length=64), nullable=True),
        sa.Column('rule_version', sa.String(length=16), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_dec_trans_hist_decision_id', 'decision_transition_history', ['decision_id'])
    op.create_index('idx_dec_trans_hist_prev_id', 'decision_transition_history', ['previous_decision_id'])
    op.create_index('idx_dec_trans_hist_created_at', 'decision_transition_history', ['created_at'])

    # 3. Decision Verifications
    op.create_table(
        'decision_verifications',
        sa.Column('verification_id', sa.String(length=50), nullable=False),
        sa.Column('decision_id', sa.String(length=50), nullable=False),
        sa.Column('verifier_id', sa.String(length=100), nullable=False),
        sa.Column('verifier_reference', sa.String(length=200), nullable=True),
        sa.Column('verification_status', sa.String(length=50), nullable=False),
        sa.Column('verification_note', sa.Text(), nullable=False, server_default=''),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('verification_id'),
    )
    op.create_index('idx_decision_verif_decision_id', 'decision_verifications', ['decision_id'])
    op.create_index('idx_decision_verif_status', 'decision_verifications', ['verification_status'])
    op.create_index('idx_decision_verif_verified_at', 'decision_verifications', ['verified_at'])


def downgrade() -> None:
    op.drop_index('idx_decision_verif_verified_at', table_name='decision_verifications')
    op.drop_index('idx_decision_verif_status', table_name='decision_verifications')
    op.drop_index('idx_decision_verif_decision_id', table_name='decision_verifications')
    op.drop_table('decision_verifications')

    op.drop_index('idx_dec_trans_hist_created_at', table_name='decision_transition_history')
    op.drop_index('idx_dec_trans_hist_prev_id', table_name='decision_transition_history')
    op.drop_index('idx_dec_trans_hist_decision_id', table_name='decision_transition_history')
    op.drop_table('decision_transition_history')

    op.drop_index('idx_decision_assessment_state', table_name='decision_assessments')
    op.drop_index('idx_decision_assessment_hazard_eval_id', table_name='decision_assessments')
    op.drop_index('idx_decision_assessment_expires_at', table_name='decision_assessments')
    op.drop_index('idx_decision_assessment_version', table_name='decision_assessments')
    op.drop_index('idx_decision_assessment_created_at', table_name='decision_assessments')
    op.drop_table('decision_assessments')

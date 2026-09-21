"""Add Phase 2A Evidence Foundation tables (source_registry, evidence_records, evidence_lineage, claim_registry, runtime_evidence_bundles)

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-19 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Source Registry
    op.create_table(
        'source_registry',
        sa.Column('source_id', sa.String(length=50), nullable=False, comment='Unique source identifier'),
        sa.Column('source_name', sa.String(length=200), nullable=False),
        sa.Column('authority', sa.String(length=200), nullable=False),
        sa.Column('source_type', sa.String(length=100), nullable=False),
        sa.Column('authority_level', sa.String(length=10), nullable=False, comment='E0 to E5 hierarchy tier'),
        sa.Column('product_id', sa.String(length=100), nullable=True),
        sa.Column('version', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('base_url', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('supported_classes', sa.JSON(), nullable=False),
        sa.Column('license_notes', sa.Text(), nullable=True),
        sa.Column('provenance_requirements', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('source_id'),
    )
    op.create_index('idx_source_registry_authority_level', 'source_registry', ['authority_level'])
    op.create_index('idx_source_registry_active', 'source_registry', ['is_active'])

    # 2. Evidence Records
    op.create_table(
        'evidence_records',
        sa.Column('evidence_id', sa.String(length=50), nullable=False, comment='Unique evidence ID'),
        sa.Column('source_id', sa.String(length=50), nullable=False),
        sa.Column('evidence_class', sa.String(length=50), nullable=False),
        sa.Column('raw_field', sa.String(length=100), nullable=False),
        sa.Column('raw_value', sa.JSON(), nullable=True),
        sa.Column('raw_unit', sa.String(length=50), nullable=True),
        sa.Column('normalized_field', sa.String(length=100), nullable=False),
        sa.Column('normalized_value', sa.JSON(), nullable=True),
        sa.Column('normalized_unit', sa.String(length=50), nullable=True),
        sa.Column('quality_state', sa.String(length=20), nullable=False, server_default='VALID'),
        sa.Column('quality_flags', sa.JSON(), nullable=False),
        sa.Column('temporal', sa.JSON(), nullable=False),
        sa.Column('spatial', sa.JSON(), nullable=True),
        sa.Column('raw_payload', sa.JSON(), nullable=True),
        sa.Column('provenance', sa.JSON(), nullable=False),
        sa.Column('derived_from', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('evidence_id'),
        sa.ForeignKeyConstraint(['source_id'], ['source_registry.source_id'], ondelete='CASCADE'),
    )
    op.create_index('idx_evidence_source_id', 'evidence_records', ['source_id'])
    op.create_index('idx_evidence_class', 'evidence_records', ['evidence_class'])
    op.create_index('idx_evidence_normalized_field', 'evidence_records', ['normalized_field'])
    op.create_index('idx_evidence_quality_state', 'evidence_records', ['quality_state'])
    op.create_index('idx_evidence_created_at', 'evidence_records', ['created_at'])

    # 3. Evidence Lineage
    op.create_table(
        'evidence_lineage',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('parent_evidence_id', sa.String(length=50), nullable=False),
        sa.Column('child_evidence_id', sa.String(length=50), nullable=False),
        sa.Column('derivation_step', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_lineage_parent', 'evidence_lineage', ['parent_evidence_id'])
    op.create_index('idx_lineage_child', 'evidence_lineage', ['child_evidence_id'])

    # 4. Claim Registry
    op.create_table(
        'claim_registry',
        sa.Column('claim_id', sa.String(length=50), nullable=False),
        sa.Column('claim_text', sa.Text(), nullable=False),
        sa.Column('evidence_references', sa.JSON(), nullable=False),
        sa.Column('applicability', sa.Text(), nullable=False),
        sa.Column('what_it_proves', sa.Text(), nullable=False),
        sa.Column('what_it_does_not_prove', sa.Text(), nullable=False),
        sa.Column('supported_component', sa.String(length=50), nullable=False),
        sa.Column('permitted_wording', sa.JSON(), nullable=False),
        sa.Column('prohibited_wording', sa.JSON(), nullable=False),
        sa.Column('lifecycle_status', sa.String(length=20), nullable=False, server_default='DRAFT'),
        sa.Column('exact_locator', sa.String(length=200), nullable=True),
        sa.Column('geography', sa.String(length=100), nullable=True),
        sa.Column('time_basis', sa.String(length=100), nullable=True),
        sa.Column('source_version', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('claim_id'),
    )
    op.create_index('idx_claim_lifecycle', 'claim_registry', ['lifecycle_status'])
    op.create_index('idx_claim_component', 'claim_registry', ['supported_component'])

    # 5. Runtime Evidence Bundles
    op.create_table(
        'runtime_evidence_bundles',
        sa.Column('bundle_id', sa.String(length=50), nullable=False),
        sa.Column('claim_ids', sa.JSON(), nullable=False),
        sa.Column('evidence_ids', sa.JSON(), nullable=False),
        sa.Column('bundle_payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('bundle_id'),
    )
    op.create_index('idx_bundle_created_at', 'runtime_evidence_bundles', ['created_at'])


def downgrade() -> None:
    op.drop_index('idx_bundle_created_at', table_name='runtime_evidence_bundles')
    op.drop_table('runtime_evidence_bundles')

    op.drop_index('idx_claim_component', table_name='claim_registry')
    op.drop_index('idx_claim_lifecycle', table_name='claim_registry')
    op.drop_table('claim_registry')

    op.drop_index('idx_lineage_child', table_name='evidence_lineage')
    op.drop_index('idx_lineage_parent', table_name='evidence_lineage')
    op.drop_table('evidence_lineage')

    op.drop_index('idx_evidence_created_at', table_name='evidence_records')
    op.drop_index('idx_evidence_quality_state', table_name='evidence_records')
    op.drop_index('idx_evidence_normalized_field', table_name='evidence_records')
    op.drop_index('idx_evidence_class', table_name='evidence_records')
    op.drop_index('idx_evidence_source_id', table_name='evidence_records')
    op.drop_table('evidence_records')

    op.drop_index('idx_source_registry_active', table_name='source_registry')
    op.drop_index('idx_source_registry_authority_level', table_name='source_registry')
    op.drop_table('source_registry')

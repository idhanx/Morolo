"""Initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-04-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create document_jobs table
    op.create_table(
        'document_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('storage_key', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('scan_type', sa.String(length=50), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('risk_band', sa.String(length=50), nullable=True),
        sa.Column('om_entity_fqn', sa.String(length=500), nullable=True),
        sa.Column('redacted_storage_key', sa.String(length=500), nullable=True),
        sa.Column('redacted_om_entity_fqn', sa.String(length=500), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('risk_score >= 0 AND risk_score <= 100', name='check_risk_score_range'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_document_jobs_risk_band', 'document_jobs', ['risk_band'])
    op.create_index('idx_document_jobs_status_created', 'document_jobs', ['status', 'created_at'])
    op.create_index(op.f('ix_document_jobs_file_hash'), 'document_jobs', ['file_hash'])
    op.create_index(op.f('ix_document_jobs_status'), 'document_jobs', ['status'])

    # Create pii_entities table
    op.create_table(
        'pii_entities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('subtype', sa.String(length=100), nullable=True),
        sa.Column('start_offset', sa.Integer(), nullable=False),
        sa.Column('end_offset', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('end_offset > start_offset', name='check_end_after_start'),
        sa.CheckConstraint('start_offset >= 0', name='check_start_offset_positive'),
        sa.ForeignKeyConstraint(['job_id'], ['document_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_pii_entities_job_type', 'pii_entities', ['job_id', 'entity_type'])
    op.create_index(op.f('ix_pii_entities_entity_type'), 'pii_entities', ['entity_type'])

    # Create redaction_reports table
    op.create_table(
        'redaction_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('redaction_level', sa.String(length=50), nullable=False),
        sa.Column('total_entities_redacted', sa.Integer(), nullable=False),
        sa.Column('risk_score_before', sa.Float(), nullable=False),
        sa.Column('risk_score_after', sa.Float(), nullable=False),
        sa.Column('redacted_storage_key', sa.String(length=500), nullable=True),
        sa.Column('report_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('risk_score_after >= 0 AND risk_score_after <= 100', name='check_risk_after_range'),
        sa.CheckConstraint('risk_score_before >= 0 AND risk_score_before <= 100', name='check_risk_before_range'),
        sa.CheckConstraint('total_entities_redacted >= 0', name='check_entities_positive'),
        sa.ForeignKeyConstraint(['job_id'], ['document_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_redaction_reports_job_created', 'redaction_reports', ['job_id', 'created_at'])

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('actor', sa.String(length=255), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['document_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_logs_action_timestamp', 'audit_logs', ['action', 'timestamp'])
    op.create_index('idx_audit_logs_job_timestamp', 'audit_logs', ['job_id', 'timestamp'])
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'])
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_audit_logs_timestamp'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_index('idx_audit_logs_job_timestamp', table_name='audit_logs')
    op.drop_index('idx_audit_logs_action_timestamp', table_name='audit_logs')
    op.drop_table('audit_logs')
    
    op.drop_index('idx_redaction_reports_job_created', table_name='redaction_reports')
    op.drop_table('redaction_reports')
    
    op.drop_index(op.f('ix_pii_entities_entity_type'), table_name='pii_entities')
    op.drop_index('idx_pii_entities_job_type', table_name='pii_entities')
    op.drop_table('pii_entities')
    
    op.drop_index(op.f('ix_document_jobs_status'), table_name='document_jobs')
    op.drop_index(op.f('ix_document_jobs_file_hash'), table_name='document_jobs')
    op.drop_index('idx_document_jobs_status_created', table_name='document_jobs')
    op.drop_index('idx_document_jobs_risk_band', table_name='document_jobs')
    op.drop_table('document_jobs')

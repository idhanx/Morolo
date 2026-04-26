"""Add unique constraint on file_hash

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unique constraint on file_hash to prevent duplicate uploads."""
    # Create unique index on file_hash
    op.create_unique_constraint(
        'uq_document_jobs_file_hash',
        'document_jobs',
        ['file_hash']
    )


def downgrade() -> None:
    """Remove unique constraint on file_hash."""
    op.drop_constraint(
        'uq_document_jobs_file_hash',
        'document_jobs'
    )

"""add_job_ttl - Add TTL support for jobs

Revision ID: 002
Revises: 001
Create Date: 2025-12-16 00:00:00.000000

This migration adds TTL (Time To Live) mechanism for LLM Gateway jobs:
- default_ttl_seconds column on service_flavors (NULL = never expire)
- expires_at column on jobs (computed at job creation)
- Partial index for efficient cleanup queries
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================================
    # 1. Add default_ttl_seconds column to service_flavors
    # ==========================================================================
    op.add_column(
        'service_flavors',
        sa.Column(
            'default_ttl_seconds',
            sa.Integer(),
            nullable=True,
            comment='Default TTL for jobs in seconds. NULL = never expire.'
        )
    )

    # ==========================================================================
    # 2. Add expires_at column to jobs
    # ==========================================================================
    op.add_column(
        'jobs',
        sa.Column(
            'expires_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='When this job expires and can be cleaned up. NULL = never.'
        )
    )

    # ==========================================================================
    # 3. Create partial index for efficient cleanup queries
    # ==========================================================================
    op.execute("""
        CREATE INDEX idx_jobs_expires_at
        ON jobs (expires_at)
        WHERE expires_at IS NOT NULL;
    """)


def downgrade() -> None:
    # Drop partial index first
    op.execute("DROP INDEX IF EXISTS idx_jobs_expires_at;")

    # Drop columns
    op.drop_column('jobs', 'expires_at')
    op.drop_column('service_flavors', 'default_ttl_seconds')

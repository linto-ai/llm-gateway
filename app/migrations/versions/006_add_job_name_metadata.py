"""add_job_name_metadata - Store caller-supplied names on the job

Revision ID: 006
Revises: 005
Create Date: 2026-05-20 00:00:00.000000

Two human-readable names captured when the job is created so they can be
exposed as standard template placeholders at export time:
  * conversation_name : name of the originating conversation/session
  * organization_name : name of the organization (companion to organization_id)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('conversation_name', sa.String(255), nullable=True))
    op.add_column('jobs', sa.Column('organization_name', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('jobs', 'organization_name')
    op.drop_column('jobs', 'conversation_name')

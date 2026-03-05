"""make_celery_task_id_nullable - Allow jobs without Celery tasks (e.g. chat)

Revision ID: 005
Revises: 004
Create Date: 2026-03-05 00:00:00.000000

Chat jobs are persisted for analytics but have no Celery task.
PostgreSQL allows multiple NULLs in a UNIQUE column.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('jobs', 'celery_task_id',
                    existing_type=sa.String(255),
                    nullable=True)


def downgrade() -> None:
    # Delete chat jobs (celery_task_id IS NULL) before restoring NOT NULL
    op.execute("DELETE FROM jobs WHERE celery_task_id IS NULL")
    op.alter_column('jobs', 'celery_task_id',
                    existing_type=sa.String(255),
                    nullable=False)

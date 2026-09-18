"""template_owner - uploader of a document template

Revision ID: 009
Revises: 008
Create Date: 2026-09-18 00:00:00.000000

Adds `document_templates.owner_user_id`: the external user ID of whoever
uploaded the template (LinTO Studio user). The access lists only say who can
see a template; ownership is needed so a personal template can be opened to the
whole organization and still be edited/deleted by its author.

Backfilled from the legacy `user_id` column (single-user scoped templates were
always uploaded by that user).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document_templates",
        sa.Column("owner_user_id", sa.String(100), nullable=True),
    )
    op.execute(
        "UPDATE document_templates SET owner_user_id = user_id "
        "WHERE user_id IS NOT NULL AND user_id <> ''"
    )
    op.create_index("idx_templates_owner_user", "document_templates", ["owner_user_id"])


def downgrade() -> None:
    op.drop_index("idx_templates_owner_user", table_name="document_templates")
    op.drop_column("document_templates", "owner_user_id")

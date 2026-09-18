"""template_icon - icon shown on a template card

Revision ID: 010
Revises: 009
Create Date: 2026-09-18 12:00:00.000000

Adds `document_templates.icon`: a Phosphor icon name picked by the admin,
rendered by LinTO Studio on the publication template cards.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '010'
down_revision: Union[str, None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("document_templates", sa.Column("icon", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("document_templates", "icon")

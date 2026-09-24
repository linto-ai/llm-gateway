"""service_display_order - explicit ordering of the service list

Revision ID: 012
Revises: 011
Create Date: 2026-09-24 18:00:00.000000

Adds `services.display_order`: services are listed by ascending display_order,
then newest first. Clients showing the list (LinTO Studio tabs, Meet picking the
first service) get a stable, admin-controlled order. Existing services get 100,
so the current order is unchanged until an admin sets a position.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '012'
down_revision: Union[str, None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "services",
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="100"),
    )
    op.create_index("idx_services_display_order", "services", ["display_order"])


def downgrade() -> None:
    op.drop_index("idx_services_display_order", table_name="services")
    op.drop_column("services", "display_order")

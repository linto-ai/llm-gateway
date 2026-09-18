"""service_scopes - usage scopes on services

Revision ID: 011
Revises: 010
Create Date: 2026-09-18 14:00:00.000000

Adds `services.scopes`: the client products a service is listed for ("linto"
for LinTO Studio, "meet", "twake"...). Orthogonal to the access lists
(allowed_organization_ids / allowed_user_ids), which say who may use it.
Existing services get the default scope "linto".
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '011'
down_revision: Union[str, None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "services",
        sa.Column(
            "scopes", postgresql.ARRAY(sa.String(50)),
            nullable=False, server_default="{linto}",
        ),
    )
    op.create_index("idx_services_scopes", "services", ["scopes"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("idx_services_scopes", table_name="services")
    op.drop_column("services", "scopes")

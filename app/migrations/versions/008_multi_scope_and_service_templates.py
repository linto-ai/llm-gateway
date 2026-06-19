"""multi_scope_and_service_templates - multi org/user scoping + service<->template links

Revision ID: 008
Revises: 007
Create Date: 2026-06-19 00:00:00.000000

Adds list-based scoping (allowed_organization_ids / allowed_user_ids) to both
`services` and `document_templates`, so a resource can be granted to several
organizations and/or several users instead of a single one. The legacy scalar
columns (services.organization_id, document_templates.organization_id/user_id)
are kept and back-compat-derived so existing clients (LinTO Studio) keep working.

Also adds the `service_document_templates` junction table letting admins choose
which document templates are available for which service (empty set => the
service falls back to the global default template).

The per-org unique constraints on services (uq_service_name_org / route) and the
document_templates check_user_requires_org constraint no longer fit the
multi-scope model and are dropped. DROP ... IF EXISTS keeps this idempotent.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ARRAY = postgresql.ARRAY(sa.String(100))


def upgrade() -> None:
    # 1. Add multi-scope array columns (NOT NULL, default empty array).
    for table in ("services", "document_templates"):
        op.add_column(
            table,
            sa.Column(
                "allowed_organization_ids", _ARRAY,
                nullable=False, server_default="{}",
            ),
        )
        op.add_column(
            table,
            sa.Column(
                "allowed_user_ids", _ARRAY,
                nullable=False, server_default="{}",
            ),
        )

    # 2. Backfill existing single-scope values into the new lists.
    op.execute(
        "UPDATE services SET allowed_organization_ids = ARRAY[organization_id] "
        "WHERE organization_id IS NOT NULL AND organization_id <> ''"
    )
    op.execute(
        "UPDATE document_templates SET allowed_organization_ids = ARRAY[organization_id] "
        "WHERE organization_id IS NOT NULL AND organization_id <> ''"
    )
    op.execute(
        "UPDATE document_templates SET allowed_user_ids = ARRAY[user_id] "
        "WHERE user_id IS NOT NULL AND user_id <> ''"
    )

    # 3. Drop constraints that no longer fit the multi-scope model.
    op.execute("ALTER TABLE services DROP CONSTRAINT IF EXISTS uq_service_name_org")
    op.execute("ALTER TABLE services DROP CONSTRAINT IF EXISTS uq_service_route_org")
    op.execute("ALTER TABLE document_templates DROP CONSTRAINT IF EXISTS check_user_requires_org")

    # 4. Indexes: plain index on services.name + GIN indexes for array membership.
    op.create_index("idx_services_name", "services", ["name"])
    op.create_index(
        "idx_services_allowed_orgs", "services",
        ["allowed_organization_ids"], postgresql_using="gin",
    )
    op.create_index(
        "idx_services_allowed_users", "services",
        ["allowed_user_ids"], postgresql_using="gin",
    )
    op.create_index(
        "idx_templates_allowed_orgs", "document_templates",
        ["allowed_organization_ids"], postgresql_using="gin",
    )
    op.create_index(
        "idx_templates_allowed_users", "document_templates",
        ["allowed_user_ids"], postgresql_using="gin",
    )

    # 5. Service <-> document template junction table.
    op.create_table(
        "service_document_templates",
        sa.Column(
            "service_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("services.id", ondelete="CASCADE"), primary_key=True,
        ),
        sa.Column(
            "document_template_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_templates.id", ondelete="CASCADE"), primary_key=True,
        ),
    )
    op.create_index(
        "idx_service_document_templates_template",
        "service_document_templates", ["document_template_id"],
    )


def downgrade() -> None:
    # Reverse order. Backfilled list data is lost; legacy scalar columns remain.
    op.drop_index("idx_service_document_templates_template", table_name="service_document_templates")
    op.drop_table("service_document_templates")

    op.drop_index("idx_templates_allowed_users", table_name="document_templates")
    op.drop_index("idx_templates_allowed_orgs", table_name="document_templates")
    op.drop_index("idx_services_allowed_users", table_name="services")
    op.drop_index("idx_services_allowed_orgs", table_name="services")
    op.drop_index("idx_services_name", table_name="services")

    # Re-add the dropped constraints (best-effort on downgrade).
    op.execute(
        "ALTER TABLE document_templates ADD CONSTRAINT check_user_requires_org "
        "CHECK ((user_id IS NULL) OR (organization_id IS NOT NULL))"
    )
    op.create_unique_constraint("uq_service_route_org", "services", ["route", "organization_id"])
    op.create_unique_constraint("uq_service_name_org", "services", ["name", "organization_id"])

    for table in ("document_templates", "services"):
        op.drop_column(table, "allowed_user_ids")
        op.drop_column(table, "allowed_organization_ids")

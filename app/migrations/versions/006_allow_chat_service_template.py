"""allow_chat_service_template - Add 'chat' to the service_templates service_type CHECK constraint

Revision ID: 006
Revises: 005
Create Date: 2026-06-17 00:00:00.000000

The service_templates.check_template_service_type CHECK constraint (created in
001) listed 6 service types and omitted 'chat', even though 'chat' is a valid
service type (registry app/core/service_types.py, seeded into the service_types
lookup table by migration 004). Creating a service *template* of type 'chat'
would therefore violate the constraint. This aligns the constraint with the
canonical registry so chat works end to end on both fresh deploys and updates.

DROP ... IF EXISTS keeps this idempotent and resilient if a database diverged.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Canonical set incl. 'chat' (matches app/core/service_types.py).
_WITH_CHAT = (
    "service_type IN ('summary', 'translation', 'categorization', "
    "'diarization_correction', 'speaker_correction', 'chat', 'generic')"
)
# Original set from migration 001 (no 'chat').
_WITHOUT_CHAT = (
    "service_type IN ('summary', 'translation', 'categorization', "
    "'diarization_correction', 'speaker_correction', 'generic')"
)


def upgrade() -> None:
    op.execute(
        "ALTER TABLE service_templates "
        "DROP CONSTRAINT IF EXISTS check_template_service_type;"
    )
    op.execute(
        "ALTER TABLE service_templates "
        f"ADD CONSTRAINT check_template_service_type CHECK ({_WITH_CHAT});"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE service_templates "
        "DROP CONSTRAINT IF EXISTS check_template_service_type;"
    )
    op.execute(
        "ALTER TABLE service_templates "
        f"ADD CONSTRAINT check_template_service_type CHECK ({_WITHOUT_CHAT});"
    )

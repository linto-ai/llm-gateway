"""add_chat_service_type - Seed 'chat' into service_types table

Revision ID: 004
Revises: 003
Create Date: 2026-02-27 00:00:00.000000

Adds the 'chat' service type which supports interactive chat
with context injection (system prompt only, no chunking/reduce).
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO service_types (code, name, description, is_system, is_active, display_order, supports_reduce, supports_chunking, default_processing_mode)
        VALUES (
            'chat',
            '{"en": "Chat", "fr": "Chat"}'::jsonb,
            '{"en": "Interactive chat with context injection", "fr": "Chat interactif avec injection de contexte"}'::jsonb,
            true, true, 5, false, false, 'single_pass'
        )
        ON CONFLICT (code) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DELETE FROM service_types WHERE code = 'chat' AND is_system = true;")

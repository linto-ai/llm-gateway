"""security_level_integer - Convert security_level from text to integer

Revision ID: 003
Revises: 002
Create Date: 2025-01-21 00:00:00.000000

This migration converts security_level from text-based values to integers:
- 'insecure' -> 0 (Lowest security)
- 'sensitive' -> 1 (Medium security)
- 'secure' -> 2 (Highest security)

Affected tables:
- providers: security_level NOT NULL with default 1
- models: security_level NULLABLE
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================================
    # 1. Providers table: Convert security_level from VARCHAR to INTEGER
    # ==========================================================================

    # Drop existing check constraint
    op.execute("ALTER TABLE providers DROP CONSTRAINT IF EXISTS check_security_level;")

    # Add temporary column for integer values
    op.add_column('providers', sa.Column('security_level_new', sa.Integer(), nullable=True))

    # Migrate data: 'insecure' -> 0, 'sensitive' -> 1, 'secure' -> 2
    op.execute("""
        UPDATE providers SET security_level_new = CASE
            WHEN security_level = 'insecure' THEN 0
            WHEN security_level = 'sensitive' THEN 1
            WHEN security_level = 'secure' THEN 2
            ELSE 1
        END;
    """)

    # Drop old column
    op.drop_column('providers', 'security_level')

    # Rename new column to security_level
    op.execute("ALTER TABLE providers RENAME COLUMN security_level_new TO security_level;")

    # Set NOT NULL and default
    op.execute("ALTER TABLE providers ALTER COLUMN security_level SET NOT NULL;")
    op.execute("ALTER TABLE providers ALTER COLUMN security_level SET DEFAULT 1;")

    # Add check constraint for integer values
    op.execute("""
        ALTER TABLE providers ADD CONSTRAINT check_security_level
        CHECK (security_level IN (0, 1, 2));
    """)

    # Recreate index for security_level
    op.execute("DROP INDEX IF EXISTS idx_providers_security;")
    op.execute("CREATE INDEX idx_providers_security ON providers (security_level);")

    # ==========================================================================
    # 2. Models table: Convert security_level from VARCHAR to INTEGER (nullable)
    # ==========================================================================

    # Add temporary column for integer values
    op.add_column('models', sa.Column('security_level_new', sa.Integer(), nullable=True))

    # Migrate data: 'insecure' -> 0, 'sensitive' -> 1, 'secure' -> 2, NULL stays NULL
    op.execute("""
        UPDATE models SET security_level_new = CASE
            WHEN security_level = 'insecure' THEN 0
            WHEN security_level = 'sensitive' THEN 1
            WHEN security_level = 'secure' THEN 2
            ELSE NULL
        END;
    """)

    # Drop old column
    op.drop_column('models', 'security_level')

    # Rename new column to security_level
    op.execute("ALTER TABLE models RENAME COLUMN security_level_new TO security_level;")

    # Add check constraint for integer values (allowing NULL)
    op.execute("""
        ALTER TABLE models ADD CONSTRAINT check_model_security_level
        CHECK (security_level IS NULL OR security_level IN (0, 1, 2));
    """)


def downgrade() -> None:
    # ==========================================================================
    # 1. Models table: Revert to VARCHAR
    # ==========================================================================

    # Drop check constraint
    op.execute("ALTER TABLE models DROP CONSTRAINT IF EXISTS check_model_security_level;")

    # Add temporary column for text values
    op.add_column('models', sa.Column('security_level_old', sa.String(50), nullable=True))

    # Migrate data back: 0 -> 'insecure', 1 -> 'sensitive', 2 -> 'secure'
    op.execute("""
        UPDATE models SET security_level_old = CASE
            WHEN security_level = 0 THEN 'insecure'
            WHEN security_level = 1 THEN 'sensitive'
            WHEN security_level = 2 THEN 'secure'
            ELSE NULL
        END;
    """)

    # Drop integer column
    op.drop_column('models', 'security_level')

    # Rename old column back
    op.execute("ALTER TABLE models RENAME COLUMN security_level_old TO security_level;")

    # ==========================================================================
    # 2. Providers table: Revert to VARCHAR
    # ==========================================================================

    # Drop check constraint and index
    op.execute("ALTER TABLE providers DROP CONSTRAINT IF EXISTS check_security_level;")
    op.execute("DROP INDEX IF EXISTS idx_providers_security;")

    # Add temporary column for text values
    op.add_column('providers', sa.Column('security_level_old', sa.String(20), nullable=True))

    # Migrate data back: 0 -> 'insecure', 1 -> 'sensitive', 2 -> 'secure'
    op.execute("""
        UPDATE providers SET security_level_old = CASE
            WHEN security_level = 0 THEN 'insecure'
            WHEN security_level = 1 THEN 'sensitive'
            WHEN security_level = 2 THEN 'secure'
            ELSE 'sensitive'
        END;
    """)

    # Drop integer column
    op.drop_column('providers', 'security_level')

    # Rename old column back
    op.execute("ALTER TABLE providers RENAME COLUMN security_level_old TO security_level;")

    # Set NOT NULL
    op.execute("ALTER TABLE providers ALTER COLUMN security_level SET NOT NULL;")

    # Recreate original check constraint
    op.execute("""
        ALTER TABLE providers ADD CONSTRAINT check_security_level
        CHECK (security_level IN ('secure', 'sensitive', 'insecure'));
    """)

    # Recreate index
    op.execute("CREATE INDEX idx_providers_security ON providers (security_level);")

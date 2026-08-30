"""enable postgis extension

Revision ID: 0001
Revises:
Create Date: 2026-08-29 00:00:00.000000

Enables the PostGIS extension so every spatial table created in later phases
(states, districts, tehsils, hazard polygons, NWP grid cells) can rely on it.

Note: ``CREATE EXTENSION IF NOT EXISTS postgis`` is the only operation. No domain
tables are created here — B2 establishes the database foundation only.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable the PostGIS extension in the public schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")


def downgrade() -> None:
    """Disable the PostGIS extension (safe while no spatial tables depend on it).

    Later phases that add spatial objects must not downgrade past this migration
    without first dropping their dependent objects.
    """
    op.execute("DROP EXTENSION IF EXISTS postgis CASCADE;")

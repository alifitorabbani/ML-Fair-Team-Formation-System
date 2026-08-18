"""add is_eliminated and bracket match schedule fields

Revision ID: d17e5be6ca0a
Revises: 
Create Date: 2026-08-18 11:26:06.562720
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd17e5be6ca0a'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add is_eliminated to tournament_teams
    op.execute(
        "ALTER TABLE tournament_teams ADD COLUMN IF NOT EXISTS is_eliminated BOOLEAN DEFAULT FALSE NOT NULL"
    )

    # Add schedule fields to bracket_match_maps
    op.execute(
        "ALTER TABLE bracket_match_maps ADD COLUMN IF NOT EXISTS scheduled_date VARCHAR NULL"
    )
    op.execute(
        "ALTER TABLE bracket_match_maps ADD COLUMN IF NOT EXISTS start_time VARCHAR NULL"
    )
    op.execute(
        "ALTER TABLE bracket_match_maps ADD COLUMN IF NOT EXISTS end_time VARCHAR NULL"
    )

    # Add bracket fields to matches
    op.execute(
        "ALTER TABLE matches ADD COLUMN IF NOT EXISTS next_match_id VARCHAR NULL"
    )
    op.execute(
        "ALTER TABLE matches ADD COLUMN IF NOT EXISTS loser_next_match_id VARCHAR NULL"
    )
    op.execute(
        "ALTER TABLE matches ADD COLUMN IF NOT EXISTS participant_source_a VARCHAR NULL"
    )
    op.execute(
        "ALTER TABLE matches ADD COLUMN IF NOT EXISTS participant_source_b VARCHAR NULL"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE tournament_teams DROP COLUMN IF EXISTS is_eliminated")
    op.execute("ALTER TABLE bracket_match_maps DROP COLUMN IF EXISTS scheduled_date")
    op.execute("ALTER TABLE bracket_match_maps DROP COLUMN IF EXISTS start_time")
    op.execute("ALTER TABLE bracket_match_maps DROP COLUMN IF EXISTS end_time")
    op.execute("ALTER TABLE matches DROP COLUMN IF EXISTS next_match_id")
    op.execute("ALTER TABLE matches DROP COLUMN IF EXISTS loser_next_match_id")
    op.execute("ALTER TABLE matches DROP COLUMN IF EXISTS participant_source_a")
    op.execute("ALTER TABLE matches DROP COLUMN IF EXISTS participant_source_b")

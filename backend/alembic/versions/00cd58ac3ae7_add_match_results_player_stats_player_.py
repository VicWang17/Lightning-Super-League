"""add_match_results_player_stats_player_id_mv_index

Revision ID: 00cd58ac3ae7
Revises: 906eabf3fa06
Create Date: 2026-06-26 19:17:15.911923

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '00cd58ac3ae7'
down_revision: Union[str, Sequence[str], None] = '906eabf3fa06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add multi-valued index on match_results.player_stats.player_id."""
    op.execute(
        """
        CREATE INDEX idx_match_results_player_stats_player_id
        ON match_results ((CAST(player_stats->"$[*].player_id" AS CHAR(36) ARRAY)))
        """
    )


def downgrade() -> None:
    """Drop the multi-valued index."""
    op.execute(
        """
        DROP INDEX idx_match_results_player_stats_player_id ON match_results
        """
    )

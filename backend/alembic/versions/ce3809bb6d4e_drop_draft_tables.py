"""drop_draft_tables

Revision ID: ce3809bb6d4e
Revises: b2f4f8a6c901
Create Date: 2026-06-01 16:21:01.839166

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce3809bb6d4e'
down_revision: Union[str, Sequence[str], None] = 'b2f4f8a6c901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop draft-related tables (simplified closed-loop design)."""
    op.drop_table('draft_selections', if_exists=True)
    op.drop_table('draft_preferences', if_exists=True)
    op.drop_table('draft_pool_players', if_exists=True)
    op.drop_table('draft_pools', if_exists=True)


def downgrade() -> None:
    """Recreate draft-related tables."""
    op.create_table(
        'draft_pools',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('season_id', sa.String(36), sa.ForeignKey('seasons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('league_id', sa.String(36), sa.ForeignKey('leagues.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='preparing'),
        sa.Column('opened_at_day', sa.Integer, nullable=True),
        sa.Column('draft_day', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
    )
    op.create_table(
        'draft_pool_players',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('draft_pool_id', sa.String(36), sa.ForeignKey('draft_pools.id', ondelete='CASCADE'), nullable=False),
        sa.Column('player_id', sa.String(36), sa.ForeignKey('players.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_team_id', sa.String(36), sa.ForeignKey('teams.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='available'),
        sa.Column('rank_snapshot', sa.Integer, nullable=True),
        sa.Column('selected_by_team_id', sa.String(36), sa.ForeignKey('teams.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
    )
    op.create_table(
        'draft_preferences',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('draft_pool_id', sa.String(36), sa.ForeignKey('draft_pools.id', ondelete='CASCADE'), nullable=False),
        sa.Column('team_id', sa.String(36), sa.ForeignKey('teams.id', ondelete='CASCADE'), nullable=False),
        sa.Column('player_id', sa.String(36), sa.ForeignKey('players.id', ondelete='CASCADE'), nullable=False),
        sa.Column('priority', sa.Integer, nullable=False, default=1),
        sa.Column('excluded', sa.Boolean, nullable=False, default=False),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
    )
    op.create_table(
        'draft_selections',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('draft_pool_id', sa.String(36), sa.ForeignKey('draft_pools.id', ondelete='CASCADE'), nullable=False),
        sa.Column('team_id', sa.String(36), sa.ForeignKey('teams.id', ondelete='CASCADE'), nullable=False),
        sa.Column('player_id', sa.String(36), sa.ForeignKey('players.id', ondelete='CASCADE'), nullable=False),
        sa.Column('season_id', sa.String(36), sa.ForeignKey('seasons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('selection_order', sa.Integer, nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
    )

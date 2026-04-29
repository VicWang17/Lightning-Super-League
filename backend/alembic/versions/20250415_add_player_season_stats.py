"""add_player_season_stats

Revision ID: 20250415_add_player_season_stats
Revises: 20250411_add_season_system
Create Date: 2025-04-15 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20250415_add_player_season_stats'
down_revision: Union[str, Sequence[str], None] = '20250411_add_season_system'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - 新增球员赛季统计表"""
    op.create_table('player_season_stats',
        sa.Column('player_id', sa.String(length=36), nullable=False),
        sa.Column('season_id', sa.String(length=36), nullable=False),
        sa.Column('team_id', sa.String(length=36), nullable=True),
        sa.Column('league_id', sa.String(length=36), nullable=True),
        sa.Column('matches_played', sa.Integer(), nullable=False),
        sa.Column('minutes_played', sa.Integer(), nullable=False),
        sa.Column('goals', sa.Integer(), nullable=False),
        sa.Column('assists', sa.Integer(), nullable=False),
        sa.Column('yellow_cards', sa.Integer(), nullable=False),
        sa.Column('red_cards', sa.Integer(), nullable=False),
        sa.Column('clean_sheets', sa.Integer(), nullable=False),
        sa.Column('average_rating', sa.DECIMAL(precision=3, scale=1), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['league_id'], ['leagues.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('player_id', 'season_id', name='uix_player_season')
    )
    op.create_index(op.f('ix_player_season_stats_league_id'), 'player_season_stats', ['league_id'], unique=False)
    op.create_index(op.f('ix_player_season_stats_player_id'), 'player_season_stats', ['player_id'], unique=False)
    op.create_index(op.f('ix_player_season_stats_season_id'), 'player_season_stats', ['season_id'], unique=False)
    op.create_index(op.f('ix_player_season_stats_team_id'), 'player_season_stats', ['team_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema"""
    op.drop_index(op.f('ix_player_season_stats_team_id'), table_name='player_season_stats')
    op.drop_index(op.f('ix_player_season_stats_season_id'), table_name='player_season_stats')
    op.drop_index(op.f('ix_player_season_stats_player_id'), table_name='player_season_stats')
    op.drop_index(op.f('ix_player_season_stats_league_id'), table_name='player_season_stats')
    op.drop_table('player_season_stats')

"""add_player_awards_table

Revision ID: 540386d64cea
Revises: 30deaf0048f7
Create Date: 2026-06-11 02:01:47.045961

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '540386d64cea'
down_revision: Union[str, Sequence[str], None] = '30deaf0048f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create AwardType enum
    award_type_enum = sa.Enum(
        'match_mvp',
        'league_team_of_season',
        'league_best_fw', 'league_best_mf', 'league_best_df', 'league_best_gk',
        'league_golden_boot', 'league_playmaker', 'league_golden_glove', 'league_golden_wall',
        'cup_golden_boot', 'cup_playmaker', 'cup_golden_glove', 'cup_golden_wall',
        'season_best_player',
        'season_best_fw', 'season_best_mf', 'season_best_df', 'season_best_gk',
        'season_golden_boot', 'season_playmaker', 'season_golden_glove', 'season_golden_wall',
        name='awardtype'
    )
    award_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'player_awards',
        sa.Column('player_id', sa.String(length=36), nullable=False),
        sa.Column('season_id', sa.String(length=36), nullable=False),
        sa.Column('season_number', sa.Integer(), nullable=False),
        sa.Column('award_type', sa.Enum(
            'match_mvp',
            'league_team_of_season',
            'league_best_fw', 'league_best_mf', 'league_best_df', 'league_best_gk',
            'league_golden_boot', 'league_playmaker', 'league_golden_glove', 'league_golden_wall',
            'cup_golden_boot', 'cup_playmaker', 'cup_golden_glove', 'cup_golden_wall',
            'season_best_player',
            'season_best_fw', 'season_best_mf', 'season_best_df', 'season_best_gk',
            'season_golden_boot', 'season_playmaker', 'season_golden_glove', 'season_golden_wall',
            name='awardtype'
        ), nullable=False),
        sa.Column('award_level', sa.Enum('match', 'league', 'season', 'cup', name='awardlevel'), nullable=False),
        sa.Column('league_id', sa.String(length=36), nullable=True),
        sa.Column('cup_id', sa.String(length=36), nullable=True),
        sa.Column('fixture_id', sa.String(length=36), nullable=True),
        sa.Column('position', sa.String(length=10), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['cup_id'], ['cup_competitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['fixture_id'], ['fixtures.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['league_id'], ['leagues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('player_id', 'season_id', 'award_type', 'league_id', 'cup_id', 'fixture_id', name='uk_player_award')
    )
    op.create_index(op.f('ix_player_awards_award_type'), 'player_awards', ['award_type'], unique=False)
    op.create_index(op.f('ix_player_awards_league_id'), 'player_awards', ['league_id'], unique=False)
    op.create_index(op.f('ix_player_awards_player_id'), 'player_awards', ['player_id'], unique=False)
    op.create_index(op.f('ix_player_awards_season_id'), 'player_awards', ['season_id'], unique=False)
    op.create_index(op.f('ix_player_awards_season_id_award_type'), 'player_awards', ['season_id', 'award_type'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_player_awards_season_id_award_type'), table_name='player_awards')
    op.drop_index(op.f('ix_player_awards_season_id'), table_name='player_awards')
    op.drop_index(op.f('ix_player_awards_player_id'), table_name='player_awards')
    op.drop_index(op.f('ix_player_awards_league_id'), table_name='player_awards')
    op.drop_index(op.f('ix_player_awards_award_type'), table_name='player_awards')
    op.drop_table('player_awards')
    sa.Enum(name='awardtype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='awardlevel').drop(op.get_bind(), checkfirst=True)

"""add_season_system

Revision ID: 20250411_add_season_system
Revises: 116888f2eb4f
Create Date: 2025-04-11 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '20250411_add_season_system'
down_revision: Union[str, Sequence[str], None] = '116888f2eb4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - 赛季系统重构"""
    
    # 0. 清理旧数据（如果有）
    op.execute("DELETE FROM seasons WHERE 1=1")
    
    # 1. 修改 seasons 表
    # 添加新字段
    op.add_column('seasons', sa.Column('season_number', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('seasons', sa.Column('current_day', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('seasons', sa.Column('current_league_round', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('seasons', sa.Column('current_cup_round', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('seasons', sa.Column('total_days', sa.Integer(), nullable=False, server_default='42'))
    op.add_column('seasons', sa.Column('league_days', sa.Integer(), nullable=False, server_default='30'))
    op.add_column('seasons', sa.Column('cup_start_day', sa.Integer(), nullable=False, server_default='6'))
    op.add_column('seasons', sa.Column('cup_interval', sa.Integer(), nullable=False, server_default='3'))
    op.add_column('seasons', sa.Column('offseason_start', sa.Integer(), nullable=False, server_default='31'))
    
    # 修改 status 字段使用新的枚举值
    op.alter_column('seasons', 'status',
                    existing_type=sa.Enum('UPCOMING', 'ONGOING', 'COMPLETED', name='seasonstatus'),
                    type_=sa.Enum('PENDING', 'ONGOING', 'FINISHED', name='seasonstatus'),
                    existing_nullable=False)
    
    # end_date 改为可为空（赛季结束后再填充）
    op.alter_column('seasons', 'end_date',
                    existing_type=sa.DateTime(),
                    nullable=True)
    
    # 添加索引
    op.create_index(op.f('ix_seasons_season_number'), 'seasons', ['season_number'], unique=True)
    
    # 2. 删除旧的 matches 表（如果存在）
    try:
        op.drop_index('ix_matches_away_team_id', table_name='matches')
        op.drop_index('ix_matches_home_team_id', table_name='matches')
        op.drop_index('ix_matches_league_id', table_name='matches')
        op.drop_index('ix_matches_matchday', table_name='matches')
        op.drop_index('ix_matches_scheduled_at', table_name='matches')
        op.drop_index('ix_matches_season_id', table_name='matches')
        op.drop_index('ix_matches_status', table_name='matches')
        op.drop_table('matches')
    except:
        pass  # 表可能不存在
    
    # 3. 创建杯赛表（先创建，因为fixtures表外键引用它）
    op.create_table('cup_competitions',
        sa.Column('season_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('eligible_league_levels', sa.JSON(), nullable=False),
        sa.Column('total_teams', sa.Integer(), nullable=False),
        sa.Column('has_group_stage', sa.Boolean(), nullable=False),
        sa.Column('group_count', sa.Integer(), nullable=False),
        sa.Column('teams_per_group', sa.Integer(), nullable=False),
        sa.Column('group_rounds', sa.Integer(), nullable=False),
        sa.Column('current_round', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'ONGOING', 'FINISHED', name='seasonstatus'), nullable=False),
        sa.Column('winner_team_id', sa.String(length=36), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['winner_team_id'], ['teams.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cup_competitions_season_id'), 'cup_competitions', ['season_id'], unique=False)
    
    # 4. 创建杯赛小组表（仅闪电杯使用）
    op.create_table('cup_groups',
        sa.Column('competition_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=10), nullable=False),
        sa.Column('team_ids', sa.JSON(), nullable=False),
        sa.Column('standings', sa.JSON(), nullable=True),
        sa.Column('qualified_team_ids', sa.JSON(), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['competition_id'], ['cup_competitions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cup_groups_competition_id'), 'cup_groups', ['competition_id'], unique=False)
    
    # 5. 创建杯赛轮空球队表
    op.create_table('cup_bye_teams',
        sa.Column('competition_id', sa.String(length=36), nullable=False),
        sa.Column('team_id', sa.String(length=36), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['competition_id'], ['cup_competitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cup_bye_teams_competition_id'), 'cup_bye_teams', ['competition_id'], unique=False)
    
    # 6. 创建新的 fixtures 表（联赛+杯赛统一）
    op.create_table('fixtures',
        sa.Column('season_id', sa.String(length=36), nullable=False),
        sa.Column('fixture_type', sa.Enum('LEAGUE', 'CUP_LIGHTNING_GROUP', 'CUP_LIGHTNING_KNOCKOUT', 'CUP_JENNY', name='fixturetype'), nullable=False),
        sa.Column('season_day', sa.Integer(), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('league_id', sa.String(length=36), nullable=True),
        sa.Column('cup_competition_id', sa.String(length=36), nullable=True),
        sa.Column('cup_group_name', sa.String(length=10), nullable=True),
        sa.Column('cup_stage', sa.String(length=20), nullable=True),
        sa.Column('home_team_id', sa.String(length=36), nullable=False),
        sa.Column('away_team_id', sa.String(length=36), nullable=False),
        sa.Column('home_score', sa.Integer(), nullable=True),
        sa.Column('away_score', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('SCHEDULED', 'ONGOING', 'FINISHED', name='fixturestatus'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['away_team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cup_competition_id'], ['cup_competitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['home_team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['league_id'], ['leagues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fixtures_away_team_id'), 'fixtures', ['away_team_id'], unique=False)
    op.create_index(op.f('ix_fixtures_cup_competition_id'), 'fixtures', ['cup_competition_id'], unique=False)
    op.create_index(op.f('ix_fixtures_fixture_type'), 'fixtures', ['fixture_type'], unique=False)
    op.create_index(op.f('ix_fixtures_home_team_id'), 'fixtures', ['home_team_id'], unique=False)
    op.create_index(op.f('ix_fixtures_league_id'), 'fixtures', ['league_id'], unique=False)
    op.create_index(op.f('ix_fixtures_scheduled_at'), 'fixtures', ['scheduled_at'], unique=False)
    op.create_index(op.f('ix_fixtures_season_day'), 'fixtures', ['season_day'], unique=False)
    op.create_index(op.f('ix_fixtures_season_id'), 'fixtures', ['season_id'], unique=False)
    op.create_index(op.f('ix_fixtures_status'), 'fixtures', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema"""
    # 删除新创建的表（顺序：先子表后父表）
    op.drop_index(op.f('ix_cup_groups_competition_id'), table_name='cup_groups')
    op.drop_table('cup_groups')
    
    op.drop_index(op.f('ix_cup_bye_teams_competition_id'), table_name='cup_bye_teams')
    op.drop_table('cup_bye_teams')
    
    op.drop_index(op.f('ix_cup_competitions_season_id'), table_name='cup_competitions')
    op.drop_table('cup_competitions')
    
    op.drop_index(op.f('ix_fixtures_status'), table_name='fixtures')
    op.drop_index(op.f('ix_fixtures_season_id'), table_name='fixtures')
    op.drop_index(op.f('ix_fixtures_season_day'), table_name='fixtures')
    op.drop_index(op.f('ix_fixtures_scheduled_at'), table_name='fixtures')
    op.drop_index(op.f('ix_fixtures_league_id'), table_name='fixtures')
    op.drop_index(op.f('ix_fixtures_home_team_id'), table_name='fixtures')
    op.drop_index(op.f('ix_fixtures_fixture_type'), table_name='fixtures')
    op.drop_index(op.f('ix_fixtures_cup_competition_id'), table_name='fixtures')
    op.drop_index(op.f('ix_fixtures_away_team_id'), table_name='fixtures')
    op.drop_table('fixtures')
    
    # 恢复旧的 matches 表
    op.create_table('matches',
        sa.Column('season_id', sa.String(length=36), nullable=False),
        sa.Column('league_id', sa.String(length=36), nullable=False),
        sa.Column('matchday', sa.Integer(), nullable=False),
        sa.Column('home_team_id', sa.String(length=36), nullable=False),
        sa.Column('away_team_id', sa.String(length=36), nullable=False),
        sa.Column('home_score', sa.Integer(), nullable=True),
        sa.Column('away_score', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('SCHEDULED', 'ONGOING', 'FINISHED', 'POSTPONED', 'CANCELLED', name='matchstatus'), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('home_possession', sa.Integer(), nullable=True),
        sa.Column('away_possession', sa.Integer(), nullable=True),
        sa.Column('home_shots', sa.Integer(), nullable=True),
        sa.Column('away_shots', sa.Integer(), nullable=True),
        sa.Column('home_shots_on_target', sa.Integer(), nullable=True),
        sa.Column('away_shots_on_target', sa.Integer(), nullable=True),
        sa.Column('mvp_player_id', sa.String(length=36), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['away_team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['home_team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['league_id'], ['leagues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['mvp_player_id'], ['players.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_matches_away_team_id'), 'matches', ['away_team_id'], unique=False)
    op.create_index(op.f('ix_matches_home_team_id'), 'matches', ['home_team_id'], unique=False)
    op.create_index(op.f('ix_matches_league_id'), 'matches', ['league_id'], unique=False)
    op.create_index(op.f('ix_matches_matchday'), 'matches', ['matchday'], unique=False)
    op.create_index(op.f('ix_matches_scheduled_at'), 'matches', ['scheduled_at'], unique=False)
    op.create_index(op.f('ix_matches_season_id'), 'matches', ['season_id'], unique=False)
    op.create_index(op.f('ix_matches_status'), 'matches', ['status'], unique=False)
    
    # 移除 seasons 表的新字段
    op.drop_index(op.f('ix_seasons_season_number'), table_name='seasons')
    op.drop_column('seasons', 'offseason_start')
    op.drop_column('seasons', 'cup_interval')
    op.drop_column('seasons', 'cup_start_day')
    op.drop_column('seasons', 'league_days')
    op.drop_column('seasons', 'total_days')
    op.drop_column('seasons', 'current_cup_round')
    op.drop_column('seasons', 'current_league_round')
    op.drop_column('seasons', 'current_day')
    op.drop_column('seasons', 'season_number')
    
    # 恢复 seasons 表原来的字段类型
    op.alter_column('seasons', 'end_date',
                    existing_type=sa.DateTime(),
                    nullable=False)
    op.alter_column('seasons', 'status',
                    existing_type=sa.Enum('PENDING', 'ONGOING', 'FINISHED', name='seasonstatus'),
                    type_=sa.Enum('UPCOMING', 'ONGOING', 'COMPLETED', name='seasonstatus'),
                    existing_nullable=False)

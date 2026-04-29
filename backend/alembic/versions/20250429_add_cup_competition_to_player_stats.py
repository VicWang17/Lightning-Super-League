"""add_cup_competition_to_player_stats

Revision ID: 20250429_add_cup_competition_to_player_stats
Revises: 20250415_add_player_season_stats
Create Date: 2025-04-29 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250429_add_cup_competition_to_player_stats'
down_revision: Union[str, Sequence[str], None] = '20250415_add_player_season_stats'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - 为球员赛季统计表添加杯赛关联，支持杯赛射手榜/助攻榜"""
    # 添加 cup_competition_id 列
    op.add_column('player_season_stats', sa.Column('cup_competition_id', sa.String(length=36), nullable=True))
    
    # 添加外键约束
    op.create_foreign_key(
        'fk_player_season_stats_cup_competition',
        'player_season_stats', 'cup_competitions',
        ['cup_competition_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # 添加索引
    op.create_index(op.f('ix_player_season_stats_cup_competition_id'), 'player_season_stats', ['cup_competition_id'], unique=False)
    
    # 删除旧唯一约束
    op.drop_constraint('uix_player_season', 'player_season_stats', type_='unique')
    
    # 添加新唯一约束（支持联赛和杯赛独立统计）
    op.create_unique_constraint('uix_player_season_competition', 'player_season_stats', ['player_id', 'season_id', 'league_id', 'cup_competition_id'])


def downgrade() -> None:
    """Downgrade schema"""
    # 删除新唯一约束
    op.drop_constraint('uix_player_season_competition', 'player_season_stats', type_='unique')
    
    # 恢复旧唯一约束
    op.create_unique_constraint('uix_player_season', 'player_season_stats', ['player_id', 'season_id'])
    
    # 删除索引
    op.drop_index(op.f('ix_player_season_stats_cup_competition_id'), table_name='player_season_stats')
    
    # 删除外键
    op.drop_constraint('fk_player_season_stats_cup_competition', 'player_season_stats', type_='foreignkey')
    
    # 删除列
    op.drop_column('player_season_stats', 'cup_competition_id')

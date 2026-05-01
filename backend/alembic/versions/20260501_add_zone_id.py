"""add_zone_id_to_league_systems

Revision ID: 20260501_add_zone_id
Revises: 20250429_add_cup_competition_to_player_stats
Create Date: 2025-04-29 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260501_add_zone_id'
down_revision: Union[str, Sequence[str], None] = '20250429_add_cup_competition_to_player_stats'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - 为联赛体系表添加 zone_id 字段，支持多区扩展"""
    # 添加 zone_id 列（幂等：先检查是否存在）
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('league_systems')]
    
    if 'zone_id' not in columns:
        op.add_column('league_systems', sa.Column('zone_id', sa.Integer(), nullable=False, server_default='1'))
        op.create_index(op.f('ix_league_systems_zone_id'), 'league_systems', ['zone_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema"""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    indexes = [idx['name'] for idx in inspector.get_indexes('league_systems')]
    columns = [col['name'] for col in inspector.get_columns('league_systems')]
    
    if 'ix_league_systems_zone_id' in indexes:
        op.drop_index(op.f('ix_league_systems_zone_id'), table_name='league_systems')
    
    if 'zone_id' in columns:
        op.drop_column('league_systems', 'zone_id')

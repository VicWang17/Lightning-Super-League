"""add_cup_to_record_scope

Revision ID: 906eabf3fa06
Revises: 6868de019995
Create Date: 2026-06-25 20:05:58.830124

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '906eabf3fa06'
down_revision: Union[str, Sequence[str], None] = '6868de019995'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # records.scope 枚举增加 CUP，否则杯赛纪录无法写入数据库
    op.alter_column(
        'records',
        'scope',
        existing_type=sa.Enum('WORLD', 'LEAGUE', 'TEAM', name='recordscope'),
        type_=sa.Enum('WORLD', 'LEAGUE', 'TEAM', 'CUP', name='recordscope'),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # 先删除 CUP 维度的纪录，避免枚举收缩后数据不合法
    op.execute("DELETE FROM records WHERE scope = 'CUP'")
    op.alter_column(
        'records',
        'scope',
        existing_type=sa.Enum('WORLD', 'LEAGUE', 'TEAM', 'CUP', name='recordscope'),
        type_=sa.Enum('WORLD', 'LEAGUE', 'TEAM', name='recordscope'),
        existing_nullable=False,
    )

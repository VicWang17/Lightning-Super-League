"""add_set_piece_takers

Revision ID: b3ef909386d6
Revises: ae579cd31544
Create Date: 2026-08-04 14:20:31.681312

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3ef909386d6'
down_revision: Union[str, Sequence[str], None] = 'ae579cd31544'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_NAME = 'team_tactics' AND COLUMN_NAME = 'set_piece_takers' "
            "AND TABLE_SCHEMA = DATABASE()"
        )
    )
    if result.scalar() == 0:
        # MySQL JSON 列不能直接设 DEFAULT，先 nullable 加入
        op.add_column(
            'team_tactics',
            sa.Column('set_piece_takers', sa.JSON(), nullable=True)
        )
    # 已有记录补空对象
    op.execute(sa.text("UPDATE team_tactics SET set_piece_takers = '{}' WHERE set_piece_takers IS NULL"))
    # 填充后改为 NOT NULL
    op.alter_column('team_tactics', 'set_piece_takers', existing_type=sa.JSON(), nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_NAME = 'team_tactics' AND COLUMN_NAME = 'set_piece_takers' "
            "AND TABLE_SCHEMA = DATABASE()"
        )
    )
    if result.scalar() > 0:
        op.drop_column('team_tactics', 'set_piece_takers')

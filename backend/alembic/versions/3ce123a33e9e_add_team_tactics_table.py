"""add_team_tactics_table

Revision ID: 3ce123a33e9e
Revises: 540386d64cea
Create Date: 2026-06-15 17:40:46.996260

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3ce123a33e9e'
down_revision: Union[str, Sequence[str], None] = '540386d64cea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # ===== 新建 team_tactics 表 =====
    result = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.TABLES "
            "WHERE TABLE_NAME = 'team_tactics' AND TABLE_SCHEMA = DATABASE()"
        )
    )
    if result.scalar() == 0:
        op.create_table(
            'team_tactics',
            sa.Column('team_id', sa.String(length=36), nullable=False),
            sa.Column('formation_id', sa.String(length=8), nullable=False, server_default='F01'),
            sa.Column('lineup_player_ids', sa.JSON(), nullable=False),
            sa.Column('bench_player_ids', sa.JSON(), nullable=False),
            sa.Column('team_instructions', sa.JSON(), nullable=False),
            sa.Column('set_piece_instructions', sa.JSON(), nullable=False),
            sa.Column('substitution_rules', sa.JSON(), nullable=False),
            sa.Column('ai_profile', sa.JSON(), nullable=True),
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('team_id', name='uix_team_tactics_team_id')
        )
        op.create_index(op.f('ix_team_tactics_team_id'), 'team_tactics', ['team_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.TABLES "
            "WHERE TABLE_NAME = 'team_tactics' AND TABLE_SCHEMA = DATABASE()"
        )
    )
    if result.scalar() > 0:
        op.drop_index(op.f('ix_team_tactics_team_id'), table_name='team_tactics')
        op.drop_table('team_tactics')

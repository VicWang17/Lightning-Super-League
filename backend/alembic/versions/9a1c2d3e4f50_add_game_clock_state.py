"""add_game_clock_state

Revision ID: 9a1c2d3e4f50
Revises: 7c2a91d4b6f0
Create Date: 2026-05-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a1c2d3e4f50"
down_revision: Union[str, Sequence[str], None] = "7c2a91d4b6f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_clock_states",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("speed", sa.Float(), nullable=False),
        sa.Column("virtual_anchor", sa.DateTime(), nullable=False),
        sa.Column("real_anchor", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("game_clock_states")

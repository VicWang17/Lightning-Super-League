"""add_match_results

Revision ID: 7c2a91d4b6f0
Revises: e0d9f135233e
Create Date: 2026-05-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c2a91d4b6f0"
down_revision: Union[str, Sequence[str], None] = "e0d9f135233e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "match_results",
        sa.Column("fixture_id", sa.String(length=36), nullable=False),
        sa.Column("engine_match_id", sa.String(length=64), nullable=False),
        sa.Column("home_score", sa.Integer(), nullable=False),
        sa.Column("away_score", sa.Integer(), nullable=False),
        sa.Column("winner_team_id", sa.String(length=36), nullable=True),
        sa.Column("resolution", sa.String(length=20), nullable=False),
        sa.Column("penalty_score", sa.JSON(), nullable=True),
        sa.Column("match_stats", sa.JSON(), nullable=False),
        sa.Column("player_stats", sa.JSON(), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("narratives", sa.JSON(), nullable=False),
        sa.Column("raw_result", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["fixture_id"], ["fixtures.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["winner_team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fixture_id", name="uix_match_results_fixture"),
    )
    op.create_index(op.f("ix_match_results_engine_match_id"), "match_results", ["engine_match_id"], unique=False)
    op.create_index(op.f("ix_match_results_fixture_id"), "match_results", ["fixture_id"], unique=False)
    op.create_index(op.f("ix_match_results_winner_team_id"), "match_results", ["winner_team_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_match_results_winner_team_id"), table_name="match_results")
    op.drop_index(op.f("ix_match_results_fixture_id"), table_name="match_results")
    op.drop_index(op.f("ix_match_results_engine_match_id"), table_name="match_results")
    op.drop_table("match_results")

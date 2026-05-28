"""trim_player_persisted_fields

Revision ID: c4d2e8f91a6b
Revises: e15512f5daa9
Create Date: 2026-05-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4d2e8f91a6b"
down_revision: Union[str, Sequence[str], None] = "e15512f5daa9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove derived player fields from the players table."""
    for column_name in (
        "potential_letter",
        "market_value",
        "recommended_wage",
        "wage_ratio",
        "wage_satisfaction",
        "state_score",
        "state_updated_at",
        "matches_played",
        "goals",
        "assists",
        "yellow_cards",
        "red_cards",
        "average_rating",
        "minutes_played",
    ):
        op.drop_column("players", column_name)


def downgrade() -> None:
    """Restore previously persisted player fields."""
    op.add_column(
        "players",
        sa.Column(
            "potential_letter",
            sa.Enum("S", "A", "B", "C", "D", name="potentialletter"),
            nullable=False,
            server_default="C",
        ),
    )
    op.add_column(
        "players",
        sa.Column("market_value", sa.DECIMAL(precision=15, scale=2), nullable=False, server_default="100000.00"),
    )
    op.add_column("players", sa.Column("recommended_wage", sa.DECIMAL(precision=12, scale=2), nullable=True))
    op.add_column("players", sa.Column("wage_ratio", sa.DECIMAL(precision=5, scale=2), nullable=True))
    op.add_column("players", sa.Column("wage_satisfaction", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("players", sa.Column("state_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("players", sa.Column("state_updated_at", sa.DateTime(), nullable=True))
    op.add_column("players", sa.Column("matches_played", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("players", sa.Column("goals", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("players", sa.Column("assists", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("players", sa.Column("yellow_cards", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("players", sa.Column("red_cards", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(
        "players",
        sa.Column("average_rating", sa.DECIMAL(precision=3, scale=1), nullable=False, server_default="6.0"),
    )
    op.add_column("players", sa.Column("minutes_played", sa.Integer(), nullable=False, server_default="0"))

"""add_player_state_cache_fields

Revision ID: b2f4f8a6c901
Revises: 84dbdd46a448
Create Date: 2026-06-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b2f4f8a6c901"
down_revision: Union[str, Sequence[str], None] = "84dbdd46a448"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    if _has_column(table_name, column_name):
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    _add_column_if_missing("players", sa.Column("recent_ratings", sa.JSON(), nullable=True))
    _add_column_if_missing("players", sa.Column("recent_minutes", sa.JSON(), nullable=True))
    _add_column_if_missing("players", sa.Column("state_contract_score", sa.Integer(), nullable=False, server_default="0"))
    _add_column_if_missing("players", sa.Column("state_recent_match_score", sa.Integer(), nullable=False, server_default="0"))
    _add_column_if_missing("players", sa.Column("state_fitness_score", sa.Integer(), nullable=False, server_default="0"))
    _add_column_if_missing("players", sa.Column("state_match_load_score", sa.Integer(), nullable=False, server_default="0"))
    _add_column_if_missing("players", sa.Column("state_training_load_score", sa.Integer(), nullable=False, server_default="0"))
    _add_column_if_missing("players", sa.Column("state_morale_score", sa.Integer(), nullable=False, server_default="0"))
    _add_column_if_missing("players", sa.Column("state_attribute_modifier_pct", sa.DECIMAL(precision=6, scale=4), nullable=False, server_default="0.0000"))
    _add_column_if_missing("players", sa.Column("state_stamina_modifier", sa.DECIMAL(precision=6, scale=2), nullable=False, server_default="0.00"))


def downgrade() -> None:
    _drop_column_if_exists("players", "state_stamina_modifier")
    _drop_column_if_exists("players", "state_attribute_modifier_pct")
    _drop_column_if_exists("players", "state_morale_score")
    _drop_column_if_exists("players", "state_training_load_score")
    _drop_column_if_exists("players", "state_match_load_score")
    _drop_column_if_exists("players", "state_fitness_score")
    _drop_column_if_exists("players", "state_recent_match_score")
    _drop_column_if_exists("players", "state_contract_score")
    _drop_column_if_exists("players", "recent_minutes")
    _drop_column_if_exists("players", "recent_ratings")

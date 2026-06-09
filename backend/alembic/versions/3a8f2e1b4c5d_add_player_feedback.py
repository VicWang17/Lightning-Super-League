"""add_player_feedback

Revision ID: 3a8f2e1b4c5d
Revises: 0ccb7da51a2a
Create Date: 2026-06-09 11:54:08.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a8f2e1b4c5d'
down_revision: Union[str, Sequence[str], None] = '0ccb7da51a2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'player_feedbacks',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('player_id', sa.String(36), sa.ForeignKey('players.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('team_id', sa.String(36), sa.ForeignKey('teams.id', ondelete='SET NULL'), nullable=True),
        sa.Column('season_id', sa.String(36), sa.ForeignKey('seasons.id', ondelete='SET NULL'), nullable=True),
        sa.Column('day_number', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('player_feedbacks')

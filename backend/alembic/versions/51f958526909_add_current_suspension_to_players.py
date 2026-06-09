"""add_current_suspension_to_players

Revision ID: 51f958526909
Revises: 58f064705dd1
Create Date: 2026-06-09 17:07:03.926675

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51f958526909'
down_revision: Union[str, Sequence[str], None] = '58f064705dd1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('players', sa.Column('current_suspension', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('players', 'current_suspension')

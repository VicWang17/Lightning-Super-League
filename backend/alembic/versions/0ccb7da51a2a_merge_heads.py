"""merge_heads

Revision ID: 0ccb7da51a2a
Revises: 214e9a5954e4, 51f958526909
Create Date: 2026-06-09 17:15:08.057634

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0ccb7da51a2a'
down_revision: Union[str, Sequence[str], None] = ('214e9a5954e4', '51f958526909')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

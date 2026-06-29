"""add_renewal_to_transfer_type

Revision ID: ae579cd31544
Revises: 00cd58ac3ae7
Create Date: 2026-06-29 14:53:46.613657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae579cd31544'
down_revision: Union[str, Sequence[str], None] = '00cd58ac3ae7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 'renewal' to transfer_records.transfer_type enum."""
    op.execute(
        """
        ALTER TABLE transfer_records
        MODIFY transfer_type ENUM(
            'club_transfer',
            'release',
            'free_market_signing',
            'renewal'
        ) NOT NULL
        """
    )


def downgrade() -> None:
    """Remove 'renewal' from transfer_records.transfer_type enum."""
    op.execute(
        """
        DELETE FROM transfer_records WHERE transfer_type = 'renewal'
        """
    )
    op.execute(
        """
        ALTER TABLE transfer_records
        MODIFY transfer_type ENUM(
            'club_transfer',
            'release',
            'free_market_signing'
        ) NOT NULL
        """
    )

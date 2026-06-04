"""add_transfer_market_tables

Revision ID: 71ed170b3b68
Revises: f204b428bcd9
Create Date: 2026-06-04 00:17:48.859595

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '71ed170b3b68'
down_revision: Union[str, Sequence[str], None] = 'f204b428bcd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Create tables without circular foreign keys
    op.create_table('transfer_listings',
        sa.Column('player_id', sa.String(length=36), nullable=False),
        sa.Column('seller_team_id', sa.String(length=36), nullable=False),
        sa.Column('season_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'ACCEPTED', 'COMPLETED', 'CANCELLED', 'EXPIRED', name='transferlistingstatus'), nullable=False),
        sa.Column('market_value_snapshot', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('list_price', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('min_price', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('listed_at_day', sa.Integer(), nullable=False),
        sa.Column('decision_deadline_at', sa.DateTime(), nullable=True),
        sa.Column('last_offer_at', sa.DateTime(), nullable=True),
        sa.Column('accepted_offer_id', sa.String(length=36), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['seller_team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_transfer_listings_player_active', 'transfer_listings', ['player_id', 'status'], unique=False)
    op.create_index(op.f('ix_transfer_listings_player_id'), 'transfer_listings', ['player_id'], unique=False)
    op.create_index(op.f('ix_transfer_listings_season_id'), 'transfer_listings', ['season_id'], unique=False)
    op.create_index('ix_transfer_listings_seller', 'transfer_listings', ['seller_team_id', 'status'], unique=False)
    op.create_index(op.f('ix_transfer_listings_seller_team_id'), 'transfer_listings', ['seller_team_id'], unique=False)
    op.create_index(op.f('ix_transfer_listings_status'), 'transfer_listings', ['status'], unique=False)
    op.create_index('ix_transfer_listings_status_season', 'transfer_listings', ['status', 'season_id'], unique=False)

    op.create_table('transfer_negotiations',
        sa.Column('listing_id', sa.String(length=36), nullable=True),
        sa.Column('player_id', sa.String(length=36), nullable=False),
        sa.Column('buyer_team_id', sa.String(length=36), nullable=False),
        sa.Column('seller_team_id', sa.String(length=36), nullable=False),
        sa.Column('season_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.Enum('OPEN', 'ACCEPTED', 'REJECTED', 'EXPIRED', 'COMPLETED', 'SETTLEMENT_FAILED', name='negotiationstatus'), nullable=False),
        sa.Column('current_offer_id', sa.String(length=36), nullable=True),
        sa.Column('initial_offer_id', sa.String(length=36), nullable=True),
        sa.Column('counter_offer_id', sa.String(length=36), nullable=True),
        sa.Column('final_offer_id', sa.String(length=36), nullable=True),
        sa.Column('counter_used', sa.Boolean(), nullable=False),
        sa.Column('final_used', sa.Boolean(), nullable=False),
        sa.Column('is_listed_snapshot', sa.Boolean(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['buyer_team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['listing_id'], ['transfer_listings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['seller_team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_transfer_negotiations_buyer', 'transfer_negotiations', ['buyer_team_id', 'status'], unique=False)
    op.create_index(op.f('ix_transfer_negotiations_buyer_team_id'), 'transfer_negotiations', ['buyer_team_id'], unique=False)
    op.create_index(op.f('ix_transfer_negotiations_listing_id'), 'transfer_negotiations', ['listing_id'], unique=False)
    op.create_index(op.f('ix_transfer_negotiations_player_id'), 'transfer_negotiations', ['player_id'], unique=False)
    op.create_index(op.f('ix_transfer_negotiations_season_id'), 'transfer_negotiations', ['season_id'], unique=False)
    op.create_index('ix_transfer_negotiations_seller', 'transfer_negotiations', ['seller_team_id', 'status'], unique=False)
    op.create_index(op.f('ix_transfer_negotiations_seller_team_id'), 'transfer_negotiations', ['seller_team_id'], unique=False)
    op.create_index('ix_transfer_negotiations_status', 'transfer_negotiations', ['status', 'expires_at'], unique=False)

    op.create_table('transfer_offers',
        sa.Column('negotiation_id', sa.String(length=36), nullable=False),
        sa.Column('listing_id', sa.String(length=36), nullable=True),
        sa.Column('player_id', sa.String(length=36), nullable=False),
        sa.Column('buyer_team_id', sa.String(length=36), nullable=False),
        sa.Column('seller_team_id', sa.String(length=36), nullable=False),
        sa.Column('sender_team_id', sa.String(length=36), nullable=False),
        sa.Column('receiver_team_id', sa.String(length=36), nullable=False),
        sa.Column('season_id', sa.String(length=36), nullable=False),
        sa.Column('amount', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('market_value_snapshot', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('offer_kind', sa.Enum('INITIAL', 'COUNTER', 'FINAL', name='offerkind'), nullable=False),
        sa.Column('round_no', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('PENDING_RESPONSE', 'ACCEPTED', 'REJECTED', 'EXPIRED', 'SUPERSEDED', 'COMPLETED', 'SETTLEMENT_FAILED', 'OUTBID_CLOSED', name='offerstatus'), nullable=False),
        sa.Column('is_public', sa.Boolean(), nullable=False),
        sa.Column('parent_offer_id', sa.String(length=36), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('responded_at', sa.DateTime(), nullable=True),
        sa.Column('response_actor_team_id', sa.String(length=36), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['buyer_team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['listing_id'], ['transfer_listings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['negotiation_id'], ['transfer_negotiations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_offer_id'], ['transfer_offers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['receiver_team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['response_actor_team_id'], ['teams.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['seller_team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transfer_offers_buyer_team_id'), 'transfer_offers', ['buyer_team_id'], unique=False)
    op.create_index(op.f('ix_transfer_offers_listing_id'), 'transfer_offers', ['listing_id'], unique=False)
    op.create_index(op.f('ix_transfer_offers_negotiation_id'), 'transfer_offers', ['negotiation_id'], unique=False)
    op.create_index('ix_transfer_offers_negotiation_kind', 'transfer_offers', ['negotiation_id', 'offer_kind'], unique=False)
    op.create_index(op.f('ix_transfer_offers_player_id'), 'transfer_offers', ['player_id'], unique=False)
    op.create_index('ix_transfer_offers_public_status', 'transfer_offers', ['is_public', 'status', 'created_at'], unique=False)
    op.create_index('ix_transfer_offers_receiver', 'transfer_offers', ['receiver_team_id', 'status'], unique=False)
    op.create_index(op.f('ix_transfer_offers_season_id'), 'transfer_offers', ['season_id'], unique=False)
    op.create_index(op.f('ix_transfer_offers_seller_team_id'), 'transfer_offers', ['seller_team_id'], unique=False)
    op.create_index(op.f('ix_transfer_offers_status'), 'transfer_offers', ['status'], unique=False)

    # Step 2: Add circular foreign keys now that all tables exist
    op.create_foreign_key('fk_transfer_listings_accepted_offer', 'transfer_listings', 'transfer_offers',
                          ['accepted_offer_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_transfer_negotiations_current_offer', 'transfer_negotiations', 'transfer_offers',
                          ['current_offer_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_transfer_negotiations_initial_offer', 'transfer_negotiations', 'transfer_offers',
                          ['initial_offer_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_transfer_negotiations_counter_offer', 'transfer_negotiations', 'transfer_offers',
                          ['counter_offer_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_transfer_negotiations_final_offer', 'transfer_negotiations', 'transfer_offers',
                          ['final_offer_id'], ['id'], ondelete='SET NULL')

    op.create_table('transfer_daily_quotas',
        sa.Column('team_id', sa.String(length=36), nullable=False),
        sa.Column('season_id', sa.String(length=36), nullable=False),
        sa.Column('season_day', sa.Integer(), nullable=False),
        sa.Column('sent_offer_count', sa.Integer(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', 'season_id', 'season_day', name='uq_transfer_quota_team_season_day')
    )
    op.create_index(op.f('ix_transfer_daily_quotas_season_id'), 'transfer_daily_quotas', ['season_id'], unique=False)
    op.create_index(op.f('ix_transfer_daily_quotas_team_id'), 'transfer_daily_quotas', ['team_id'], unique=False)
    op.create_index('ix_transfer_quotas_lookup', 'transfer_daily_quotas', ['team_id', 'season_id', 'season_day'], unique=False)

    op.create_table('transfer_records',
        sa.Column('player_id', sa.String(length=36), nullable=False),
        sa.Column('from_team_id', sa.String(length=36), nullable=True),
        sa.Column('to_team_id', sa.String(length=36), nullable=True),
        sa.Column('season_id', sa.String(length=36), nullable=False),
        sa.Column('transfer_type', sa.Enum('CLUB_TRANSFER', 'RELEASE', 'FREE_MARKET_SIGNING', name='transfertype'), nullable=False),
        sa.Column('amount', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('market_value_snapshot', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('source_offer_id', sa.String(length=36), nullable=True),
        sa.Column('source_listing_id', sa.String(length=36), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=False),
        sa.Column('is_public', sa.Boolean(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['from_team_id'], ['teams.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_listing_id'], ['transfer_listings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_offer_id'], ['transfer_offers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['to_team_id'], ['teams.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transfer_records_from_team_id'), 'transfer_records', ['from_team_id'], unique=False)
    op.create_index('ix_transfer_records_player', 'transfer_records', ['player_id', 'completed_at'], unique=False)
    op.create_index(op.f('ix_transfer_records_player_id'), 'transfer_records', ['player_id'], unique=False)
    op.create_index('ix_transfer_records_public', 'transfer_records', ['is_public', 'completed_at'], unique=False)
    op.create_index(op.f('ix_transfer_records_season_id'), 'transfer_records', ['season_id'], unique=False)
    op.create_index(op.f('ix_transfer_records_to_team_id'), 'transfer_records', ['to_team_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_transfer_records_to_team_id'), table_name='transfer_records')
    op.drop_index(op.f('ix_transfer_records_season_id'), table_name='transfer_records')
    op.drop_index('ix_transfer_records_public', table_name='transfer_records')
    op.drop_index(op.f('ix_transfer_records_player_id'), table_name='transfer_records')
    op.drop_index('ix_transfer_records_player', table_name='transfer_records')
    op.drop_index(op.f('ix_transfer_records_from_team_id'), table_name='transfer_records')
    op.drop_table('transfer_records')
    op.drop_index('ix_transfer_quotas_lookup', table_name='transfer_daily_quotas')
    op.drop_index(op.f('ix_transfer_daily_quotas_team_id'), table_name='transfer_daily_quotas')
    op.drop_index(op.f('ix_transfer_daily_quotas_season_id'), table_name='transfer_daily_quotas')
    op.drop_table('transfer_daily_quotas')
    op.drop_constraint('fk_transfer_negotiations_final_offer', 'transfer_negotiations', type_='foreignkey')
    op.drop_constraint('fk_transfer_negotiations_counter_offer', 'transfer_negotiations', type_='foreignkey')
    op.drop_constraint('fk_transfer_negotiations_initial_offer', 'transfer_negotiations', type_='foreignkey')
    op.drop_constraint('fk_transfer_negotiations_current_offer', 'transfer_negotiations', type_='foreignkey')
    op.drop_constraint('fk_transfer_listings_accepted_offer', 'transfer_listings', type_='foreignkey')
    op.drop_index(op.f('ix_transfer_offers_status'), table_name='transfer_offers')
    op.drop_index(op.f('ix_transfer_offers_seller_team_id'), table_name='transfer_offers')
    op.drop_index(op.f('ix_transfer_offers_season_id'), table_name='transfer_offers')
    op.drop_index('ix_transfer_offers_receiver', table_name='transfer_offers')
    op.drop_index('ix_transfer_offers_public_status', table_name='transfer_offers')
    op.drop_index(op.f('ix_transfer_offers_player_id'), table_name='transfer_offers')
    op.drop_index('ix_transfer_offers_negotiation_kind', table_name='transfer_offers')
    op.drop_index(op.f('ix_transfer_offers_negotiation_id'), table_name='transfer_offers')
    op.drop_index(op.f('ix_transfer_offers_listing_id'), table_name='transfer_offers')
    op.drop_index(op.f('ix_transfer_offers_buyer_team_id'), table_name='transfer_offers')
    op.drop_table('transfer_offers')
    op.drop_index('ix_transfer_negotiations_status', table_name='transfer_negotiations')
    op.drop_index(op.f('ix_transfer_negotiations_seller_team_id'), table_name='transfer_negotiations')
    op.drop_index('ix_transfer_negotiations_seller', table_name='transfer_negotiations')
    op.drop_index(op.f('ix_transfer_negotiations_season_id'), table_name='transfer_negotiations')
    op.drop_index(op.f('ix_transfer_negotiations_player_id'), table_name='transfer_negotiations')
    op.drop_index(op.f('ix_transfer_negotiations_listing_id'), table_name='transfer_negotiations')
    op.drop_index(op.f('ix_transfer_negotiations_buyer_team_id'), table_name='transfer_negotiations')
    op.drop_index('ix_transfer_negotiations_buyer', table_name='transfer_negotiations')
    op.drop_table('transfer_negotiations')
    op.drop_index('ix_transfer_listings_status_season', table_name='transfer_listings')
    op.drop_index(op.f('ix_transfer_listings_status'), table_name='transfer_listings')
    op.drop_index(op.f('ix_transfer_listings_seller_team_id'), table_name='transfer_listings')
    op.drop_index('ix_transfer_listings_seller', table_name='transfer_listings')
    op.drop_index(op.f('ix_transfer_listings_season_id'), table_name='transfer_listings')
    op.drop_index(op.f('ix_transfer_listings_player_id'), table_name='transfer_listings')
    op.drop_index('ix_transfer_listings_player_active', table_name='transfer_listings')
    op.drop_table('transfer_listings')

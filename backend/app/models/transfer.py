"""
Transfer market models - 转会市场系统
按 TRANSFER-MARKET-PRD.md v0.2 实现。
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, ForeignKey, Enum, DECIMAL, JSON, DateTime, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TransferListingStatus(str, PyEnum):
    """挂牌状态"""
    ACTIVE = "active"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class NegotiationStatus(str, PyEnum):
    """报价链状态"""
    OPEN = "open"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    COMPLETED = "completed"
    SETTLEMENT_FAILED = "settlement_failed"


class OfferKind(str, PyEnum):
    """报价类型"""
    INITIAL = "initial"
    COUNTER = "counter"
    FINAL = "final"


class OfferStatus(str, PyEnum):
    """报价状态"""
    PENDING_RESPONSE = "pending_response"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"
    COMPLETED = "completed"
    SETTLEMENT_FAILED = "settlement_failed"
    OUTBID_CLOSED = "outbid_closed"


class TransferType(str, PyEnum):
    """转会记录类型"""
    CLUB_TRANSFER = "club_transfer"
    RELEASE = "release"
    FREE_MARKET_SIGNING = "free_market_signing"
    RENEWAL = "renewal"


class TransferListing(Base):
    """球员挂牌表"""
    __tablename__ = "transfer_listings"

    player_id: Mapped[str] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seller_team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[TransferListingStatus] = mapped_column(
        Enum(TransferListingStatus),
        default=TransferListingStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    market_value_snapshot: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    list_price: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    min_price: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    listed_at_day: Mapped[int] = mapped_column(Integer, nullable=False)
    decision_deadline_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_offer_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    accepted_offer_id: Mapped[str | None] = mapped_column(
        ForeignKey("transfer_offers.id", ondelete="SET NULL"),
        nullable=True,
    )
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    # 关联关系
    player: Mapped["Player"] = relationship("Player")
    seller_team: Mapped["Team"] = relationship("Team")
    season: Mapped["Season"] = relationship("Season")

    __table_args__ = (
        Index("ix_transfer_listings_status_season", "status", "season_id"),
        Index("ix_transfer_listings_player_active", "player_id", "status"),
        Index("ix_transfer_listings_seller", "seller_team_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<TransferListing(player={self.player_id}, status={self.status.value}, price={self.list_price})>"


class TransferNegotiation(Base):
    """报价链聚合表"""
    __tablename__ = "transfer_negotiations"

    listing_id: Mapped[str | None] = mapped_column(
        ForeignKey("transfer_listings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    buyer_team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seller_team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[NegotiationStatus] = mapped_column(
        Enum(NegotiationStatus),
        default=NegotiationStatus.OPEN,
        nullable=False,
    )
    current_offer_id: Mapped[str | None] = mapped_column(
        ForeignKey("transfer_offers.id", ondelete="SET NULL"),
        nullable=True,
    )
    initial_offer_id: Mapped[str | None] = mapped_column(
        ForeignKey("transfer_offers.id", ondelete="SET NULL"),
        nullable=True,
    )
    counter_offer_id: Mapped[str | None] = mapped_column(
        ForeignKey("transfer_offers.id", ondelete="SET NULL"),
        nullable=True,
    )
    final_offer_id: Mapped[str | None] = mapped_column(
        ForeignKey("transfer_offers.id", ondelete="SET NULL"),
        nullable=True,
    )
    counter_used: Mapped[bool] = mapped_column(default=False, nullable=False)
    final_used: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_listed_snapshot: Mapped[bool] = mapped_column(default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    # 关联关系
    player: Mapped["Player"] = relationship("Player")
    buyer_team: Mapped["Team"] = relationship("Team", foreign_keys=[buyer_team_id])
    seller_team: Mapped["Team"] = relationship("Team", foreign_keys=[seller_team_id])
    season: Mapped["Season"] = relationship("Season")

    __table_args__ = (
        Index("ix_transfer_negotiations_status", "status", "expires_at"),
        Index("ix_transfer_negotiations_buyer", "buyer_team_id", "status"),
        Index("ix_transfer_negotiations_seller", "seller_team_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<TransferNegotiation(player={self.player_id}, buyer={self.buyer_team_id}, status={self.status.value})>"


class TransferOffer(Base):
    """转会报价表"""
    __tablename__ = "transfer_offers"

    negotiation_id: Mapped[str] = mapped_column(
        ForeignKey("transfer_negotiations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    listing_id: Mapped[str | None] = mapped_column(
        ForeignKey("transfer_listings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    buyer_team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seller_team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    receiver_team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    market_value_snapshot: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    offer_kind: Mapped[OfferKind] = mapped_column(Enum(OfferKind), nullable=False)
    round_no: Mapped[int] = mapped_column(Integer, nullable=False)  # 1/2/3
    status: Mapped[OfferStatus] = mapped_column(
        Enum(OfferStatus),
        default=OfferStatus.PENDING_RESPONSE,
        nullable=False,
        index=True,
    )
    is_public: Mapped[bool] = mapped_column(default=True, nullable=False)
    parent_offer_id: Mapped[str | None] = mapped_column(
        ForeignKey("transfer_offers.id", ondelete="SET NULL"),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    response_actor_team_id: Mapped[str | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    # 关联关系
    negotiation: Mapped["TransferNegotiation"] = relationship("TransferNegotiation", foreign_keys=[negotiation_id])
    player: Mapped["Player"] = relationship("Player")
    buyer_team: Mapped["Team"] = relationship("Team", foreign_keys=[buyer_team_id])
    seller_team: Mapped["Team"] = relationship("Team", foreign_keys=[seller_team_id])

    __table_args__ = (
        Index("ix_transfer_offers_negotiation_kind", "negotiation_id", "offer_kind"),
        Index("ix_transfer_offers_public_status", "is_public", "status", "created_at"),
        Index("ix_transfer_offers_receiver", "receiver_team_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<TransferOffer(neg={self.negotiation_id}, kind={self.offer_kind.value}, amount={self.amount}, status={self.status.value})>"


class TransferDailyQuota(Base):
    """每日报价额度表"""
    __tablename__ = "transfer_daily_quotas"

    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_day: Mapped[int] = mapped_column(Integer, nullable=False)
    sent_offer_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("team_id", "season_id", "season_day", name="uq_transfer_quota_team_season_day"),
        Index("ix_transfer_quotas_lookup", "team_id", "season_id", "season_day"),
    )

    def __repr__(self) -> str:
        return f"<TransferDailyQuota(team={self.team_id}, day={self.season_day}, count={self.sent_offer_count})>"


class TransferRecord(Base):
    """转会历史记录表"""
    __tablename__ = "transfer_records"

    player_id: Mapped[str] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_team_id: Mapped[str | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    to_team_id: Mapped[str | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    transfer_type: Mapped[TransferType] = mapped_column(Enum(TransferType), nullable=False)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    market_value_snapshot: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    source_offer_id: Mapped[str | None] = mapped_column(
        ForeignKey("transfer_offers.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_listing_id: Mapped[str | None] = mapped_column(
        ForeignKey("transfer_listings.id", ondelete="SET NULL"),
        nullable=True,
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    is_public: Mapped[bool] = mapped_column(default=True, nullable=False)

    # 关联关系
    player: Mapped["Player"] = relationship("Player")
    from_team: Mapped["Team"] = relationship("Team", foreign_keys=[from_team_id])
    to_team: Mapped["Team"] = relationship("Team", foreign_keys=[to_team_id])
    season: Mapped["Season"] = relationship("Season")

    __table_args__ = (
        Index("ix_transfer_records_public", "is_public", "completed_at"),
        Index("ix_transfer_records_player", "player_id", "completed_at"),
    )

    def __repr__(self) -> str:
        return f"<TransferRecord(player={self.player_id}, type={self.transfer_type.value}, amount={self.amount})>"

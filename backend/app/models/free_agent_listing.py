"""
Free agent listing model - 自由市场挂牌表
按设计文档 CONTRACT-YOUTH-CLOSED-LOOP-TECH-DESIGN.md 4.3 节实现。
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, ForeignKey, Enum, DECIMAL, JSON, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class FreeAgentOrigin(str, PyEnum):
    """自由球员来源"""
    CONTRACT_EXPIRED = "contract_expired"    # 合同到期
    RELEASED = "released"                    # 解约
    DRAFT_UNSELECTED = "draft_unselected"    # 选秀未中/落选（已停用，保留兼容）
    DRAFT_DECLINED = "draft_declined"        # 选秀被放弃（已停用，保留兼容）
    AUTO_GENERATED = "auto_generated"        # 系统兜底生成
    ACADEMY_RELEASED = "academy_released"    # 青训流出新人


class ListingStatus(str, PyEnum):
    """挂牌状态"""
    ACTIVE = "active"
    SIGNED = "signed"
    EXPIRED = "expired"
    RETIRED = "retired"


class FreeAgentListing(Base):
    """自由市场挂牌表
    
    说明：
    - 自由市场页和自动签约都从这张表读取，而不是直接列出所有无队球员
    - 签字费通过 FinanceService 写入 TRANSFER 支出流水
    """
    __tablename__ = "free_agent_listings"
    
    player_id: Mapped[str] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    league_id: Mapped[str | None] = mapped_column(
        ForeignKey("leagues.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    origin: Mapped[FreeAgentOrigin] = mapped_column(
        Enum(FreeAgentOrigin),
        default=FreeAgentOrigin.CONTRACT_EXPIRED,
        nullable=False,
    )
    signing_fee: Mapped[Decimal] = mapped_column(
        DECIMAL(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    recommended_wage: Mapped[Decimal] = mapped_column(
        DECIMAL(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    listed_at_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    status: Mapped[ListingStatus] = mapped_column(
        Enum(ListingStatus),
        default=ListingStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    signed_team_id: Mapped[str | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    extra_data: Mapped[dict | None] = mapped_column(
        "metadata",  # 数据库列名仍用 metadata，避免已有数据冲突
        JSON,
        nullable=True,
        default=dict,
    )
    
    # 关联关系
    player: Mapped["Player"] = relationship("Player")
    league: Mapped["League"] = relationship("League")
    season: Mapped["Season"] = relationship("Season")
    signed_team: Mapped["Team"] = relationship("Team")
    
    __table_args__ = (
        Index("ix_free_agent_listings_status_season", "status", "season_id"),
        Index("ix_free_agent_listings_player_active", "player_id", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<FreeAgentListing(player={self.player_id}, status={self.status.value}, fee={self.signing_fee})>"

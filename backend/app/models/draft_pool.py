"""
Draft pool models - 选秀系统相关模型
按设计文档 CONTRACT-YOUTH-CLOSED-LOOP-TECH-DESIGN.md 4.6-4.9 节实现。
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, ForeignKey, Enum, JSON, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


# ==================== 选秀池 ====================

class DraftPoolStatus(str, PyEnum):
    """选秀池状态"""
    PREPARING = "preparing"           # 准备中
    PREFERENCES_OPEN = "preferences_open"  # 志愿开放
    COMPLETED = "completed"           # 已完成


class DraftPool(Base):
    """选秀池
    
    每个联赛每个赛季一条选秀池。
    """
    __tablename__ = "draft_pools"
    
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    league_id: Mapped[str] = mapped_column(
        ForeignKey("leagues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[DraftPoolStatus] = mapped_column(
        Enum(DraftPoolStatus),
        default=DraftPoolStatus.PREPARING,
        nullable=False,
    )
    opened_at_day: Mapped[int] = mapped_column(Integer, nullable=False)
    draft_day: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # 关联关系
    season: Mapped["Season"] = relationship("Season")
    league: Mapped["League"] = relationship("League")
    pool_players: Mapped[list["DraftPoolPlayer"]] = relationship(
        "DraftPoolPlayer",
        back_populates="draft_pool",
        cascade="all, delete-orphan",
    )
    preferences: Mapped[list["DraftPreference"]] = relationship(
        "DraftPreference",
        back_populates="draft_pool",
        cascade="all, delete-orphan",
    )
    selections: Mapped[list["DraftSelection"]] = relationship(
        "DraftSelection",
        back_populates="draft_pool",
        cascade="all, delete-orphan",
    )
    
    __table_args__ = (
        UniqueConstraint("season_id", "league_id", name="uix_draft_pool_season_league"),
    )
    
    def __repr__(self) -> str:
        return f"<DraftPool(season={self.season_id}, league={self.league_id}, status={self.status.value})>"


# ==================== 选秀池球员 ====================

class DraftPoolPlayerStatus(str, PyEnum):
    """选秀池球员状态"""
    AVAILABLE = "available"    # 可选
    SELECTED = "selected"      # 被选中
    FREE_MARKET = "free_market"  # 进入自由市场


class DraftPoolPlayer(Base):
    """选秀池球员"""
    __tablename__ = "draft_pool_players"
    
    draft_pool_id: Mapped[str] = mapped_column(
        ForeignKey("draft_pools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_team_id: Mapped[str | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[DraftPoolPlayerStatus] = mapped_column(
        Enum(DraftPoolPlayerStatus),
        default=DraftPoolPlayerStatus.AVAILABLE,
        nullable=False,
    )
    selected_by_team_id: Mapped[str | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )
    rank_snapshot: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # 关联关系
    draft_pool: Mapped["DraftPool"] = relationship("DraftPool", back_populates="pool_players")
    player: Mapped["Player"] = relationship("Player")
    source_team: Mapped["Team"] = relationship("Team", foreign_keys=[source_team_id])
    selected_by_team: Mapped["Team"] = relationship("Team", foreign_keys=[selected_by_team_id])
    
    def __repr__(self) -> str:
        return f"<DraftPoolPlayer(player={self.player_id}, status={self.status.value})>"


# ==================== 选秀志愿 ====================

class DraftPreference(Base):
    """选秀志愿排序
    
    玩家可提前排序志愿。未提交时默认按 rank_snapshot 排序。
    """
    __tablename__ = "draft_preferences"
    
    draft_pool_id: Mapped[str] = mapped_column(
        ForeignKey("draft_pools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    excluded: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    # 关联关系
    draft_pool: Mapped["DraftPool"] = relationship("DraftPool", back_populates="preferences")
    team: Mapped["Team"] = relationship("Team")
    player: Mapped["Player"] = relationship("Player")
    
    __table_args__ = (
        UniqueConstraint("draft_pool_id", "team_id", "player_id", name="uix_draft_preference"),
    )
    
    def __repr__(self) -> str:
        return f"<DraftPreference(team={self.team_id}, player={self.player_id}, priority={self.priority})>"


# ==================== 选秀选中结果 ====================

class DraftSelectionStatus(str, PyEnum):
    """选秀选中结果状态"""
    PENDING = "pending"               # 待签约
    SIGNED = "signed"                 # 已签约
    DECLINED = "declined"             # 玩家主动放弃
    EXPIRED = "expired"               # 24小时窗口过期
    SKIPPED_ROSTER_FULL = "skipped_roster_full"  # 阵容已满跳过


class DraftSelection(Base):
    """选秀选中结果
    
    选中后不立即入队，生成 24 小时待签约窗口。
    """
    __tablename__ = "draft_selections"
    
    draft_pool_id: Mapped[str] = mapped_column(
        ForeignKey("draft_pools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
    )
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[DraftSelectionStatus] = mapped_column(
        Enum(DraftSelectionStatus),
        default=DraftSelectionStatus.PENDING,
        nullable=False,
        index=True,
    )
    selection_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        default=dict,
    )
    
    # 关联关系
    draft_pool: Mapped["DraftPool"] = relationship("DraftPool", back_populates="selections")
    team: Mapped["Team"] = relationship("Team")
    player: Mapped["Player"] = relationship("Player")
    season: Mapped["Season"] = relationship("Season")
    
    __table_args__ = (
        UniqueConstraint("draft_pool_id", "team_id", name="uix_draft_selection_team"),
    )
    
    def __repr__(self) -> str:
        return f"<DraftSelection(team={self.team_id}, player={self.player_id}, status={self.status.value})>"

"""
Youth academy player model - 青训营在营球员表
按设计文档 CONTRACT-YOUTH-CLOSED-LOOP-TECH-DESIGN.md 4.4 节实现。
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, ForeignKey, Enum, DECIMAL, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AcademyPlayerStatus(str, PyEnum):
    """青训球员状态"""
    IN_ACADEMY = "in_academy"           # 在营中
    SIGNED = "signed"                   # 已签约入一线队
    RELEASED_TO_DRAFT = "released_to_draft"  # 放弃，进入选秀候选
    DRAFTED = "drafted"                 # 被选秀选中
    FREE_MARKET = "free_market"         # 进入自由市场


class GrowthSpeed(str, PyEnum):
    """成长速度（前端可见）"""
    FAST = "fast"
    NORMAL = "normal"
    SLOW = "slow"


class YouthAcademyPlayer(Base):
    """青训营在营状态表
    
    说明：
    - 球员基础信息仍写入 players，但 team_id 为空，直到签约进入一线队
    - 年龄 15-18，由 birth_offset 和当前赛季号计算
    """
    __tablename__ = "youth_academy_players"
    
    player_id: Mapped[str] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
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
    
    joined_season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    joined_day: Mapped[int] = mapped_column(Integer, nullable=False)
    
    status: Mapped[AcademyPlayerStatus] = mapped_column(
        Enum(AcademyPlayerStatus),
        default=AcademyPlayerStatus.IN_ACADEMY,
        nullable=False,
        index=True,
    )
    growth_speed: Mapped[GrowthSpeed] = mapped_column(
        Enum(GrowthSpeed),
        default=GrowthSpeed.NORMAL,
        nullable=False,
    )
    growth_score: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 2),
        default=Decimal("1.00"),
        nullable=False,
    )
    last_trained_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    signed_at_season: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        default=dict,
    )
    
    # 关联关系
    player: Mapped["Player"] = relationship("Player")
    team: Mapped["Team"] = relationship("Team")
    season: Mapped["Season"] = relationship("Season")
    snapshots: Mapped[list["YouthAcademySnapshot"]] = relationship(
        "YouthAcademySnapshot",
        back_populates="academy_player",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<YouthAcademyPlayer(player={self.player_id}, team={self.team_id}, status={self.status.value})>"

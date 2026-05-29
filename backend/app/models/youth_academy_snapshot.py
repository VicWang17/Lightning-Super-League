"""
Youth academy snapshot model - 青训成长曲线快照表
按设计文档 CONTRACT-YOUTH-CLOSED-LOOP-TECH-DESIGN.md 4.5 节实现。
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Integer, ForeignKey, DECIMAL, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class YouthAcademySnapshot(Base):
    """青训成长曲线快照
    
    说明：
    - 记录青训球员在营期间的 OVR 和属性变化
    - 可只保留每 2-3 天一条，避免数据膨胀（由调用方控制频率）
    """
    __tablename__ = "youth_academy_snapshots"
    
    academy_player_id: Mapped[str] = mapped_column(
        ForeignKey("youth_academy_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_day: Mapped[int] = mapped_column(Integer, nullable=False)
    
    ovr: Mapped[int] = mapped_column(Integer, nullable=False)
    attributes: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )
    growth_delta: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )
    
    # 关联关系
    academy_player: Mapped["YouthAcademyPlayer"] = relationship(
        "YouthAcademyPlayer",
        back_populates="snapshots",
    )
    season: Mapped["Season"] = relationship("Season")
    
    def __repr__(self) -> str:
        return f"<YouthAcademySnapshot(academy_player={self.academy_player_id}, day={self.season_day}, ovr={self.ovr})>"

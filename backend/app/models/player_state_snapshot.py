"""
Player state snapshot model - 球员状态快照表
按设计文档 4.3 节实现，记录每次状态聚合结果，方便调试和给玩家历史趋势。
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Integer, ForeignKey, Enum, DECIMAL, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.player import MatchForm


class PlayerStateSnapshot(Base):
    """Player state snapshot model - 球员状态快照表
    
    说明：
    - 每次状态聚合后写入一条记录
    - 保留最近 10-20 条即可，后续可定期清理
    - 为比赛引擎提供属性修正和初始 stamina 的依据
    """
    __tablename__ = "player_state_snapshots"
    
    player_id: Mapped[str] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[str | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )
    season_id: Mapped[str | None] = mapped_column(
        ForeignKey("seasons.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    source_event: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="manual",
    )
    
    # 各来源分
    contract_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recent_match_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fitness_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    match_load_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    match_rust_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    training_load_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    morale_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    total_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    visible_form: Mapped[MatchForm] = mapped_column(
        Enum(MatchForm),
        default=MatchForm.NEUTRAL,
        nullable=False,
    )
    
    attribute_modifier_pct: Mapped[Decimal] = mapped_column(
        DECIMAL(6, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    stamina_modifier: Mapped[Decimal] = mapped_column(
        DECIMAL(6, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    
    meta_data: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    
    # 关联关系
    player: Mapped["Player"] = relationship("Player", back_populates="state_snapshots")
    
    def __repr__(self) -> str:
        return (
            f"<PlayerStateSnapshot(player={self.player_id}, "
            f"total={self.total_score}, form={self.visible_form.value})>"
        )

"""
Injury treatment model - 伤病医疗记录表
按 EMERGENCY-FUND-INJURY-FINANCE-DESIGN.md 实现。
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum, DECIMAL, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TreatmentPlan(str, PyEnum):
    """医疗方案"""
    ENHANCED = "enhanced"       # 加强理疗
    SPECIALIST = "specialist"   # 专家会诊
    AGGRESSIVE = "aggressive"   # 激进复出


class InjuryTreatment(Base):
    """InjuryTreatment model - 伤病医疗记录
    
    说明：
    - 每条记录对应一次活跃伤病的唯一治疗
    - 同一次伤病只能治疗一次（unique(injury_record_id)）
    """
    __tablename__ = "injury_treatments"
    
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    player_id: Mapped[str] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    injury_record_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True
    )
    
    plan: Mapped[TreatmentPlan] = mapped_column(
        Enum(TreatmentPlan),
        nullable=False
    )
    cost: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        nullable=False
    )
    reserve_paid: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    cash_paid: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    days_before: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    days_reduced: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    days_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    residual_wear_penalty: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    recurrence_risk_bonus: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    
    # 关联关系
    team: Mapped["Team"] = relationship("Team", back_populates="injury_treatments")
    player: Mapped["Player"] = relationship("Player", back_populates="injury_treatments")
    season: Mapped["Season"] = relationship("Season", back_populates="injury_treatments")
    
    def __repr__(self) -> str:
        return (
            f"<InjuryTreatment(id={self.id}, player={self.player_id}, "
            f"plan={self.plan.value}, cost={self.cost})>"
        )

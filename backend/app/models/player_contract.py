"""
Player contract model - 球员合同历史表
按设计文档 4.2 节实现，长期支持合同历史追溯。
v1 阶段同时同步当前合同字段到 players 表，保证现有页面兼容。
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, ForeignKey, Enum, DECIMAL, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.player import ContractType, SquadRole


class ContractStatus(str, PyEnum):
    """Contract record status - 合同记录状态"""
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class PlayerContract(Base):
    """Player contract model - 球员合同表
    
    说明：
    - 每个球员的每份合同一条记录
    - 当前生效合同 status=active
    - 球员转会/解约后原合同 terminated，新球队新建 active 记录
    """
    __tablename__ = "player_contracts"
    
    player_id: Mapped[str] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[str | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    season_id: Mapped[str | None] = mapped_column(
        ForeignKey("seasons.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    contract_type: Mapped[ContractType] = mapped_column(
        Enum(ContractType),
        default=ContractType.NORMAL,
        nullable=False,
    )
    start_season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    end_season_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    wage: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    recommended_wage: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    wage_ratio: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False)
    wage_satisfaction: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    release_clause: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 2), nullable=True)
    squad_role: Mapped[SquadRole] = mapped_column(
        Enum(SquadRole),
        default=SquadRole.FIRST_TEAM,
        nullable=False,
    )
    
    status: Mapped[str] = mapped_column(
        String(20),
        default=ContractStatus.ACTIVE,
        nullable=False,
    )
    
    # 关联关系
    player: Mapped["Player"] = relationship("Player", back_populates="contracts")
    team: Mapped["Team"] = relationship("Team", back_populates="player_contracts")
    
    def __repr__(self) -> str:
        return f"<PlayerContract(player={self.player_id}, team={self.team_id}, status={self.status})>"

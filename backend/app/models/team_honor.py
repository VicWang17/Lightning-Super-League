"""
Team Honor model - 球队荣誉表
存储球队获得的联赛冠军和杯赛冠军
"""
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class HonorType(str, PyEnum):
    """荣誉类型"""
    LEAGUE_CHAMPION = "league_champion"  # 联赛冠军
    CUP_CHAMPION = "cup_champion"        # 杯赛冠军


class TeamHonor(Base):
    """TeamHonor model - 球队荣誉表

    说明：
    - 记录球队在各赛季获得的冠军荣誉
    - 联赛冠军：联赛最终积分榜第1名
    - 杯赛冠军：闪电杯/杰尼杯决赛胜者
    """
    __tablename__ = "team_honors"

    # 球队
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 赛季
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 荣誉类型
    honor_type: Mapped[HonorType] = mapped_column(
        Enum(HonorType),
        nullable=False,
        index=True,
    )

    # 赛事ID（联赛ID或杯赛competition_id）
    competition_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

    # 赛事名称（冗余，方便展示）
    competition_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # 赛事级别（联赛level，杯赛为0）
    competition_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # 关联关系
    team: Mapped["Team"] = relationship("Team", back_populates="honors")
    season: Mapped["Season"] = relationship("Season")

    def __repr__(self) -> str:
        return (
            f"<TeamHonor(team={self.team_id}, "
            f"season={self.season_id}, "
            f"type={self.honor_type.value}, "
            f"competition={self.competition_name})>"
        )

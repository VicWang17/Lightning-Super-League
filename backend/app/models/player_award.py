"""
Player Award model - 球员荣誉/奖项表
存储所有球员获得的荣誉记录
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AwardType(str, PyEnum):
    """奖项类型"""
    # 单场级
    MATCH_MVP = "match_mvp"                          # 本场最佳球员

    # 联赛级 — 最佳阵容/位置
    LEAGUE_TEAM_OF_SEASON = "league_team_of_season"  # 联赛最佳阵容
    LEAGUE_BEST_FW = "league_best_fw"                # 联赛最佳前锋
    LEAGUE_BEST_MF = "league_best_mf"                # 联赛最佳中场
    LEAGUE_BEST_DF = "league_best_df"                # 联赛最佳后卫
    LEAGUE_BEST_GK = "league_best_gk"                # 联赛最佳门将

    # 联赛级 — 数据之王
    LEAGUE_GOLDEN_BOOT = "league_golden_boot"        # 联赛金靴奖
    LEAGUE_PLAYMAKER = "league_playmaker"            # 联赛助攻王
    LEAGUE_GOLDEN_GLOVE = "league_golden_glove"      # 联赛金手套奖
    LEAGUE_GOLDEN_WALL = "league_golden_wall"        # 联赛金墙奖

    # 杯赛级 — 数据之王
    CUP_GOLDEN_BOOT = "cup_golden_boot"              # 杯赛金靴奖
    CUP_PLAYMAKER = "cup_playmaker"                  # 杯赛助攻王
    CUP_GOLDEN_GLOVE = "cup_golden_glove"            # 杯赛金手套奖
    CUP_GOLDEN_WALL = "cup_golden_wall"              # 杯赛金墙奖

    # 赛季级（全服）— 最佳球员/位置
    SEASON_BEST_PLAYER = "season_best_player"        # 年度最佳球员（闪电足球先生）
    SEASON_BEST_FW = "season_best_fw"                # 年度最佳前锋
    SEASON_BEST_MF = "season_best_mf"                # 年度最佳中场
    SEASON_BEST_DF = "season_best_df"                # 年度最佳后卫
    SEASON_BEST_GK = "season_best_gk"                # 年度最佳门将

    # 赛季级（全服）— 数据之王
    SEASON_GOLDEN_BOOT = "season_golden_boot"        # 赛季金靴奖
    SEASON_PLAYMAKER = "season_playmaker"            # 赛季助攻王
    SEASON_GOLDEN_GLOVE = "season_golden_glove"      # 赛季金手套奖
    SEASON_GOLDEN_WALL = "season_golden_wall"        # 赛季金墙奖


class AwardLevel(str, PyEnum):
    """奖项级别"""
    MATCH = "match"       # 单场
    LEAGUE = "league"     # 联赛
    CUP = "cup"           # 杯赛
    SEASON = "season"     # 赛季（全服）


class PlayerAward(Base):
    """PlayerAward model - 球员荣誉表

    说明：
    - 一张表覆盖全部奖项类型
    - match_mvp 需要 fixture_id
    - 联赛级奖项需要 league_id
    - 杯赛级奖项需要 cup_id
    - 最佳阵容/最佳位置需要 position
    """
    __tablename__ = "player_awards"

    # 球员
    player_id: Mapped[str] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 赛季
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # 奖项类型和级别
    award_type: Mapped[AwardType] = mapped_column(
        Enum(AwardType),
        nullable=False,
        index=True,
    )
    award_level: Mapped[AwardLevel] = mapped_column(
        Enum(AwardLevel),
        nullable=False,
    )

    # 关联范围
    league_id: Mapped[str | None] = mapped_column(
        ForeignKey("leagues.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    cup_id: Mapped[str | None] = mapped_column(
        ForeignKey("cup_competitions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    fixture_id: Mapped[str | None] = mapped_column(
        ForeignKey("fixtures.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # 位置信息（最佳阵容/最佳位置时用）
    position: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    # 评选依据（JSON，记录当时的评选数据）
    award_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )

    # 描述
    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # 关联关系
    player: Mapped["Player"] = relationship("Player", back_populates="awards")
    season: Mapped["Season"] = relationship("Season")
    league: Mapped["League | None"] = relationship("League")
    cup: Mapped["CupCompetition | None"] = relationship("CupCompetition")
    fixture: Mapped["Fixture | None"] = relationship("Fixture")

    def __repr__(self) -> str:
        return (
            f"<PlayerAward(player={self.player_id}, "
            f"type={self.award_type.value}, "
            f"season={self.season_number})>"
        )

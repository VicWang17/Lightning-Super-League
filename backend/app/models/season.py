"""
Season and Cup models - 赛季和杯赛模型
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum, Date, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SeasonStatus(str, PyEnum):
    """Season status enumeration"""
    PENDING = "pending"      # 待开始
    ONGOING = "ongoing"      # 进行中
    FINISHED = "finished"    # 已结束


class FixtureType(str, PyEnum):
    """Fixture type enumeration"""
    LEAGUE = "league"                    # 联赛
    CUP_LIGHTNING_GROUP = "cup_lightning_group"    # 闪电杯小组赛
    CUP_LIGHTNING_KNOCKOUT = "cup_lightning_knockout"  # 闪电杯淘汰赛
    CUP_JENNY = "cup_jenny"              # 杰尼杯
    PLAYOFF = "playoff"                  # 升降级附加赛


class FixtureStatus(str, PyEnum):
    """Fixture status enumeration"""
    SCHEDULED = "scheduled"    # 已安排
    ONGOING = "ongoing"        # 进行中
    FINISHED = "finished"      # 已结束


class Season(Base):
    """Season model - 赛季表
    
    说明：
    - 命名：第1赛季, 第2赛季...
    - 单赛季时长：42天 (30天联赛+8天杯赛+4天休赛期)
    - 所有联赛共用同一个赛季时间线
    """
    __tablename__ = "seasons"
    
    season_number: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)  # 第几赛季
    
    # 时间
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # 赛季开始时间
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)     # 赛季实际结束时间
    
    # 状态
    status: Mapped[SeasonStatus] = mapped_column(
        Enum(SeasonStatus),
        default=SeasonStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # 当前进度
    current_day: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 当前第几天 (0-42)
    current_league_round: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 当前联赛轮次 (0-30)
    current_cup_round: Mapped[int] = mapped_column(Integer, default=0, nullable=False)     # 当前杯赛轮次 (0-8)
    
    # 配置
    total_days: Mapped[int] = mapped_column(Integer, default=42, nullable=False)
    league_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    cup_start_day: Mapped[int] = mapped_column(Integer, default=6, nullable=False)  # 杯赛第1轮在第几天
    cup_interval: Mapped[int] = mapped_column(Integer, default=3, nullable=False)   # 杯赛间隔天数
    offseason_start: Mapped[int] = mapped_column(Integer, default=31, nullable=False)  # 休赛期开始
    
    # 关联关系
    fixtures: Mapped[list["Fixture"]] = relationship("Fixture", back_populates="season")
    cup_competitions: Mapped[list["CupCompetition"]] = relationship("CupCompetition", back_populates="season")
    teams: Mapped[list["Team"]] = relationship("Team", back_populates="season")
    
    def __repr__(self) -> str:
        return f"<Season(season_number={self.season_number}, status={self.status}, day={self.current_day})>"


class CupCompetition(Base):
    """CupCompetition model - 杯赛定义表
    
    说明：
    - 每个赛季有两项杯赛：闪电杯、杰尼杯
    - 记录杯赛的基本信息和状态
    """
    __tablename__ = "cup_competitions"
    
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # 闪电杯/杰尼杯
    code: Mapped[str] = mapped_column(String(20), nullable=False)  # LIGHTNING_CUP / JENNY_CUP
    
    # 参赛队伍范围
    eligible_league_levels: Mapped[list[int]] = mapped_column(JSON, nullable=False)  # [1] 或 [2,3]
    total_teams: Mapped[int] = mapped_column(Integer, nullable=False)  # 64 或 192
    
    # 赛制
    has_group_stage: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 是否有小组赛
    group_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 小组数量
    teams_per_group: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 每组球队数
    group_rounds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 小组赛轮数
    
    # 状态
    current_round: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 当前轮次
    status: Mapped[SeasonStatus] = mapped_column(
        Enum(SeasonStatus),
        default=SeasonStatus.PENDING,
        nullable=False
    )
    
    # 冠军
    winner_team_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # 关联关系
    season: Mapped["Season"] = relationship("Season", back_populates="cup_competitions")
    groups: Mapped[list["CupGroup"]] = relationship("CupGroup", back_populates="competition")
    
    def __repr__(self) -> str:
        return f"<CupCompetition(name={self.name}, season={self.season_id})>"


class CupGroup(Base):
    """CupGroup model - 杯赛小组表（仅闪电杯使用）
    
    说明：
    - 闪电杯64队分16组，每组4队
    - 记录小组内的球队和排名
    """
    __tablename__ = "cup_groups"
    
    competition_id: Mapped[str] = mapped_column(
        ForeignKey("cup_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    name: Mapped[str] = mapped_column(String(10), nullable=False)  # A, B, C... P
    
    # 球队（按当前排名顺序存储）
    team_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)  # [team1_id, team2_id, team3_id, team4_id]
    
    # 排名（动态计算，此处存储最新快照）
    standings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # {team_id: {played, won, points...}}
    
    # 晋级球队（小组赛后填充）
    qualified_team_ids: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)  # 前2名晋级
    
    # 关联关系
    competition: Mapped["CupCompetition"] = relationship("CupCompetition", back_populates="groups")
    
    def __repr__(self) -> str:
        return f"<CupGroup(name={self.name}, competition={self.competition_id})>"


class Fixture(Base):
    """Fixture model - 赛程表（联赛+杯赛统一）
    
    说明：
    - 包含所有比赛：联赛30轮 + 杯赛8轮
    - 所有比赛统一调度执行
    """
    __tablename__ = "fixtures"
    
    # 所属赛季
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # 比赛类型
    fixture_type: Mapped[FixtureType] = mapped_column(
        Enum(FixtureType),
        nullable=False,
        index=True
    )
    
    # 赛季时间线
    season_day: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 赛季第几天 (1-42)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)  # 计划开球时间
    
    # 赛事内轮次
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 在各自赛事中的轮次
    
    # 联赛相关（仅fixture_type=LEAGUE时填充）
    league_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("leagues.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # 杯赛相关
    cup_competition_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("cup_competitions.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    cup_group_name: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # 杯赛小组名（仅小组赛）
    cup_stage: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # GROUP/ROUND_32/ROUND_16/QUARTER/SEMI/FINAL
    
    # 对阵双方
    home_team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    away_team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # 比分（赛后填充）
    home_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # 比赛状态
    status: Mapped[FixtureStatus] = mapped_column(
        Enum(FixtureStatus),
        default=FixtureStatus.SCHEDULED,
        nullable=False,
        index=True
    )
    
    # 时间记录
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 关联关系
    season: Mapped["Season"] = relationship("Season", back_populates="fixtures")
    league: Mapped[Optional["League"]] = relationship("League")
    home_team: Mapped["Team"] = relationship("Team", foreign_keys=[home_team_id])
    away_team: Mapped["Team"] = relationship("Team", foreign_keys=[away_team_id])
    
    def __repr__(self) -> str:
        return f"<Fixture(day={self.season_day}, type={self.fixture_type}, {self.home_team_id} vs {self.away_team_id})>"

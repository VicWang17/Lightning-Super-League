"""
League models - 联赛体系相关模型
"""
from datetime import datetime, date
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum, Boolean, Date, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


# ==================== 联赛体系 ====================

class LeagueSystem(Base):
    """LeagueSystem model - 联赛体系表
    
    说明：
    - 共4个联赛体系：东区、西区、南区、北区
    - 每个体系独立，有自己的升降级链条
    - 每个体系包含64支球队（16队 × 4级联赛）
    """
    __tablename__ = "league_systems"
    
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # 东区/西区/南区/北区
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)  # EAST/WEST/SOUTH/NORTH
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # 配置
    max_teams_per_league: Mapped[int] = mapped_column(Integer, default=16, nullable=False)
    
    # 关联关系
    leagues: Mapped[list["League"]] = relationship("League", back_populates="system")
    
    def __repr__(self) -> str:
        return f"<LeagueSystem(id={self.id}, name={self.name}, code={self.code})>"


# ==================== 联赛 ====================

class League(Base):
    """League model - 联赛表
    
    说明：
    - 每个联赛体系包含4个级别：
      * Level 1: 顶级联赛（超级联赛）- 16支球队
      * Level 2: 次级联赛（甲级联赛）- 16支球队  
      * Level 3: 三级联赛A（乙A联赛）- 16支球队
      * Level 4: 三级联赛B（乙B联赛）- 16支球队
    - 全服总计：4个体系 × 4个联赛 = 16个联赛，256支球队
    """
    __tablename__ = "leagues"
    
    # 基本信息
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # 超级联赛/甲级联赛/乙A联赛/乙B联赛
    level: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 1=顶级, 2=次级, 3=乙A, 4=乙B
    
    # 外键
    system_id: Mapped[str] = mapped_column(
        ForeignKey("league_systems.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # 配置
    max_teams: Mapped[int] = mapped_column(Integer, default=16, nullable=False)
    
    # 升降级规则（每个体系内部）
    # 顶级联赛(1) <-> 次级联赛(2): 后4名降级，前4名升级
    # 次级联赛(2) <-> 三级联赛(3): 后4名降级，冠军直接升级(2×2=4)，亚军附加赛(2×1=2)
    promotion_spots: Mapped[int] = mapped_column(Integer, default=4, nullable=False)  # 升级名额
    relegation_spots: Mapped[int] = mapped_column(Integer, default=4, nullable=False)  # 降级名额
    has_promotion_playoff: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 是否有升级附加赛
    has_relegation_playoff: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 是否有降级附加赛
    
    # 关联关系
    system: Mapped["LeagueSystem"] = relationship("LeagueSystem", back_populates="leagues")
    teams: Mapped[list["Team"]] = relationship("Team", back_populates="league")
    standings: Mapped[list["LeagueStanding"]] = relationship("LeagueStanding", back_populates="league")
    matches: Mapped[list["Match"]] = relationship("Match", back_populates="league")
    
    def __repr__(self) -> str:
        return f"<League(id={self.id}, name={self.name}, level={self.level})>"


# ==================== 赛季 ====================

class SeasonStatus(str, PyEnum):
    """Season status enumeration"""
    UPCOMING = "upcoming"      # 即将开始
    ONGOING = "ongoing"        # 进行中
    COMPLETED = "completed"    # 已结束


class Season(Base):
    """Season model - 赛季表
    
    说明：
    - 命名：S1, S2, S3...
    - 单赛季时长：42天
    - 时间：精确到0点 (UTC)
    """
    __tablename__ = "seasons"
    
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # 如 "S1", "S2"
    
    # 时间（精确到0点）
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # 赛季开始 00:00
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)    # 赛季结束 00:00
    
    # 状态
    status: Mapped[SeasonStatus] = mapped_column(
        Enum(SeasonStatus),
        default=SeasonStatus.UPCOMING,
        nullable=False,
        index=True
    )
    
    # 转会窗口
    transfer_window_open: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    transfer_window_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    transfer_window_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # 关联关系
    teams: Mapped[list["Team"]] = relationship("Team", back_populates="season")
    standings: Mapped[list["LeagueStanding"]] = relationship("LeagueStanding", back_populates="season")
    matches: Mapped[list["Match"]] = relationship("Match", back_populates="season")
    
    def __repr__(self) -> str:
        return f"<Season(id={self.id}, name={self.name}, status={self.status})>"


# ==================== 积分榜 ====================

class LeagueStanding(Base):
    """LeagueStanding model - 联赛积分榜表
    
    说明：
    - 记录每支球队在当前赛季的积分情况
    - 排名依据：积分 -> 净胜球 -> 进球数 -> 相互对战成绩
    - 每赛季结束时会归档到 history 表
    """
    __tablename__ = "league_standings"
    
    # 联合唯一约束
    __table_args__ = (
        # 每支球队每个赛季只有一条记录
    )
    
    # 外键
    league_id: Mapped[str] = mapped_column(
        ForeignKey("leagues.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        unique=True  # 每支球队在当前赛季只有一条积分榜记录
    )
    
    # 排名
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    
    # 比赛数据
    played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 已赛场次
    won: Mapped[int] = mapped_column(Integer, default=0, nullable=False)     # 胜
    drawn: Mapped[int] = mapped_column(Integer, default=0, nullable=False)   # 平
    lost: Mapped[int] = mapped_column(Integer, default=0, nullable=False)    # 负
    
    # 进球数据
    goals_for: Mapped[int] = mapped_column(Integer, default=0, nullable=False)      # 进球
    goals_against: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 失球
    goal_difference: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 净胜球
    
    # 积分
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # 近期状态（近5场，如 "WWDLW"）
    form: Mapped[str | None] = mapped_column(String(10), nullable=True)
    
    # 升降级标记
    is_promotion_zone: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 升级区
    is_relegation_zone: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 降级区
    
    # 关联关系
    league: Mapped["League"] = relationship("League", back_populates="standings")
    season: Mapped["Season"] = relationship("Season", back_populates="standings")
    team: Mapped["Team"] = relationship("Team", back_populates="standing")
    
    def __repr__(self) -> str:
        return f"<LeagueStanding(team_id={self.team_id}, position={self.position}, points={self.points})>"
    
    def calculate_goal_difference(self) -> int:
        """Calculate goal difference"""
        return self.goals_for - self.goals_against


# ==================== 比赛 ====================

class MatchStatus(str, PyEnum):
    """Match status enumeration"""
    SCHEDULED = "scheduled"    # 已安排
    ONGOING = "ongoing"        # 进行中
    FINISHED = "finished"      # 已结束
    POSTPONED = "postponed"    # 推迟
    CANCELLED = "cancelled"    # 取消


class Match(Base):
    """Match model - 比赛表
    
    说明：
    - 联赛比赛：每个联赛体系每赛季240场比赛（30场×16队÷2）
    - 全服4个体系共960场联赛比赛
    - 杯赛暂时不做
    """
    __tablename__ = "matches"
    
    # 外键 - 赛季和联赛
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    league_id: Mapped[str] = mapped_column(
        ForeignKey("leagues.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # 轮次
    matchday: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 第几轮
    
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
    
    # 比分
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # 状态
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus),
        default=MatchStatus.SCHEDULED,
        nullable=False,
        index=True
    )
    
    # 比赛时间
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # 比赛统计（赛后填充）
    home_possession: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 主队控球率
    away_possession: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 客队控球率
    home_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)       # 主队射门
    away_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)       # 客队射门
    home_shots_on_target: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 主队射正
    away_shots_on_target: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 客队射正
    
    # MVP
    mvp_player_id: Mapped[str | None] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # 关联关系
    season: Mapped["Season"] = relationship("Season", back_populates="matches")
    league: Mapped["League"] = relationship("League", back_populates="matches")
    home_team: Mapped["Team"] = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team: Mapped["Team"] = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    mvp_player: Mapped["Player"] = relationship("Player")
    
    def __repr__(self) -> str:
        return f"<Match(id={self.id}, matchday={self.matchday}, {self.home_team_id} vs {self.away_team_id})>"

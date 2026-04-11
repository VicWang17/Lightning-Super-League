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
    fixtures: Mapped[list["Fixture"]] = relationship("Fixture")
    
    def __repr__(self) -> str:
        return f"<League(id={self.id}, name={self.name}, level={self.level})>"


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
    # 注意：season关系在新season.py中定义，这里只保留外键
    team: Mapped["Team"] = relationship("Team", back_populates="standing")
    
    def __repr__(self) -> str:
        return f"<LeagueStanding(team_id={self.team_id}, position={self.position}, points={self.points})>"
    
    def calculate_goal_difference(self) -> int:
        """Calculate goal difference"""
        return self.goals_for - self.goals_against



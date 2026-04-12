"""
Team model - 球队相关模型
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum, DECIMAL, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TeamStatus(str, PyEnum):
    """Team status enumeration"""
    ACTIVE = "active"           # 正常运营
    INACTIVE = "inactive"       # 非活跃
    SUSPENDED = "suspended"     # 被暂停


class Team(Base):
    """Team model - 球队表
    
    说明：
    - 一个用户对应一支球队（1:1）
    - 球队不能手动更换联赛，只能通过升降级
    - 初始球队由 AI 用户控制，新玩家注册后接管
    """
    __tablename__ = "teams"
    
    # 基本信息
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(10), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # 主场信息
    stadium: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(50), nullable=True)
    founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # 球队属性
    overall_rating: Mapped[int] = mapped_column(Integer, default=50, nullable=False)  # 总评
    
    # 状态
    status: Mapped[TeamStatus] = mapped_column(
        Enum(TeamStatus),
        default=TeamStatus.ACTIVE,
        nullable=False
    )
    
    # 外键关联
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True  # 确保一个用户只有一支球队
    )
    current_league_id: Mapped[str | None] = mapped_column(
        ForeignKey("leagues.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    current_season_id: Mapped[str | None] = mapped_column(
        ForeignKey("seasons.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # 关联关系
    user: Mapped["User"] = relationship("User", back_populates="team")
    league: Mapped["League"] = relationship("League", back_populates="teams")
    season: Mapped["Season"] = relationship("Season", back_populates="teams")
    finances: Mapped["TeamFinance"] = relationship("TeamFinance", back_populates="team", uselist=False)
    players: Mapped[list["Player"]] = relationship("Player", back_populates="team")
    home_fixtures: Mapped[list["Fixture"]] = relationship("Fixture", foreign_keys="Fixture.home_team_id", back_populates="home_team")
    away_fixtures: Mapped[list["Fixture"]] = relationship("Fixture", foreign_keys="Fixture.away_team_id", back_populates="away_team")
    standing: Mapped["LeagueStanding"] = relationship("LeagueStanding", back_populates="team", uselist=False)
    
    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name={self.name}, user_id={self.user_id})>"


class TeamFinance(Base):
    """TeamFinance model - 球队财务表
    
    说明：
    - 与 teams 表一对一关系
    - 记录球队的财务状况，包括资金、收入、支出等
    """
    __tablename__ = "team_finances"
    
    # 主键同时也是外键
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        primary_key=True
    )
    
    # 资金
    balance: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("10000000.00"),  # 默认初始资金 1000万
        nullable=False
    )
    
    # 周薪支出（实时计算或定期更新）
    weekly_wage_bill: Mapped[Decimal] = mapped_column(
        DECIMAL(12, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    
    # 球场相关
    stadium_capacity: Mapped[int] = mapped_column(Integer, default=5000, nullable=False)
    ticket_price: Mapped[Decimal] = mapped_column(
        DECIMAL(8, 2),
        default=Decimal("20.00"),
        nullable=False
    )
    
    # 收入
    weekly_sponsor_income: Mapped[Decimal] = mapped_column(
        DECIMAL(12, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    weekly_ticket_income: Mapped[Decimal] = mapped_column(
        DECIMAL(12, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    
    # 预算
    transfer_budget: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("5000000.00"),
        nullable=False
    )
    wage_budget: Mapped[Decimal] = mapped_column(
        DECIMAL(12, 2),
        default=Decimal("500000.00"),
        nullable=False
    )
    
    # 关联关系
    team: Mapped["Team"] = relationship("Team", back_populates="finances")
    
    def __repr__(self) -> str:
        return f"<TeamFinance(team_id={self.team_id}, balance={self.balance})>"

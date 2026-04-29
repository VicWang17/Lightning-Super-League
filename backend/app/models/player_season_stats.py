"""
Player Season Stats model - 球员赛季统计表
"""
from decimal import Decimal

from sqlalchemy import String, Integer, ForeignKey, DECIMAL, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PlayerSeasonStats(Base):
    """PlayerSeasonStats model - 球员赛季统计表
    
    说明：
    - 记录每个球员在每个赛季的统计数据
    - 支持按赛季查询射手榜、助攻榜等
    """
    __tablename__ = "player_season_stats"
    
    __table_args__ = (
        UniqueConstraint('player_id', 'season_id', name='uix_player_season'),
    )
    
    # 外键
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
    team_id: Mapped[str | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    league_id: Mapped[str | None] = mapped_column(
        ForeignKey("leagues.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # 比赛数据
    matches_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minutes_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # 进攻数据
    goals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assists: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # 纪律数据
    yellow_cards: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    red_cards: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # 门将数据
    clean_sheets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # 评分
    average_rating: Mapped[Decimal] = mapped_column(
        DECIMAL(3, 1),
        default=Decimal("6.0"),
        nullable=False
    )
    
    # 关联关系
    player: Mapped["Player"] = relationship("Player", back_populates="season_stats")
    season: Mapped["Season"] = relationship("Season")
    team: Mapped["Team | None"] = relationship("Team")
    league: Mapped["League | None"] = relationship("League")
    
    def __repr__(self) -> str:
        return f"<PlayerSeasonStats(player_id={self.player_id}, season_id={self.season_id}, goals={self.goals})>"

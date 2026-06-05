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
        UniqueConstraint('player_id', 'season_id', 'league_id', 'cup_competition_id', name='uix_player_season_competition'),
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
    cup_competition_id: Mapped[str | None] = mapped_column(
        ForeignKey("cup_competitions.id", ondelete="SET NULL"),
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

    # 进攻数据（扩展）
    shots: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shots_on_target: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dribbles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dribbles_succ: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    headers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    headers_succ: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 传球数据
    passes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passes_succ: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    key_passes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    crosses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    crosses_succ: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 防守数据
    tackles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tackles_succ: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    interceptions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clearances: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blocks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 门将数据（扩展）
    saves: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 纪律/其他数据
    fouls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fouls_drawn: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    offsides: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    turnovers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    touches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    free_kicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    free_kick_goals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    penalties: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    penalty_goals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

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
    cup_competition: Mapped["CupCompetition | None"] = relationship("CupCompetition")
    
    def __repr__(self) -> str:
        return f"<PlayerSeasonStats(player_id={self.player_id}, season_id={self.season_id}, goals={self.goals})>"

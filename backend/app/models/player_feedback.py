"""
Player feedback model - 球员每日反馈
"""
from datetime import datetime

from sqlalchemy import String, Integer, ForeignKey, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PlayerFeedback(Base):
    """Player feedback model - 球员每日反馈表
    
    存储球员每日生成的反馈文本，用于前端展示球员心态和状态。
    """
    __tablename__ = "player_feedbacks"
    
    player_id: Mapped[str] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[str | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )
    season_id: Mapped[str | None] = mapped_column(
        ForeignKey("seasons.id", ondelete="SET NULL"),
        nullable=True,
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    player: Mapped["Player"] = relationship("Player", back_populates="feedbacks")
    
    def __repr__(self) -> str:
        return f"<PlayerFeedback(player_id={self.player_id}, day={self.day_number})>"

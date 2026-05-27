"""
Persisted match engine output.
"""
from sqlalchemy import String, ForeignKey, Integer, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class MatchResult(Base):
    """Final result and event payload returned by the Go match engine."""

    __tablename__ = "match_results"

    __table_args__ = (
        UniqueConstraint("fixture_id", name="uix_match_results_fixture"),
    )

    fixture_id: Mapped[str] = mapped_column(
        ForeignKey("fixtures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    engine_match_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    home_score: Mapped[int] = mapped_column(Integer, nullable=False)
    away_score: Mapped[int] = mapped_column(Integer, nullable=False)
    winner_team_id: Mapped[str | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resolution: Mapped[str] = mapped_column(String(20), nullable=False, default="regular")
    penalty_score: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    match_stats: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    player_stats: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    events: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    narratives: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    raw_result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    fixture: Mapped["Fixture"] = relationship("Fixture")
    winner_team: Mapped["Team | None"] = relationship("Team")

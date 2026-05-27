"""
Shared virtual world clock state.
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GameClockState(Base):
    """Persisted clock state shared by API, console runners, and future workers."""

    __tablename__ = "game_clock_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="global")
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="realtime")
    speed: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    virtual_anchor: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    real_anchor: Mapped[datetime] = mapped_column(DateTime, nullable=False)

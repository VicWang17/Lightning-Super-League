"""
EventQueue ORM 模型 - 持久化虚拟时钟事件队列
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EventQueue(Base):
    """游戏事件队列"""
    __tablename__ = "event_queues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_msg: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_event_queues_status_scheduled", "status", "scheduled_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<EventQueue(id={self.id}, type={self.event_type}, "
            f"status={self.status}, scheduled={self.scheduled_at})>"
        )

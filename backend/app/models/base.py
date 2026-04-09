"""
SQLAlchemy base model with common fields
"""
from datetime import datetime
from typing import Any

from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.utils import generate_uuid


class Base(DeclarativeBase):
    """Base model with common fields"""
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    
    @property
    def is_deleted(self) -> bool:
        """Check if the record is soft deleted"""
        return self.deleted_at is not None
    
    def soft_delete(self) -> None:
        """Soft delete the record"""
        self.deleted_at = datetime.utcnow()
    
    def restore(self) -> None:
        """Restore a soft deleted record"""
        self.deleted_at = None

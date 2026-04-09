"""
User model
"""
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, Boolean, DateTime, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserStatus(str, PyEnum):
    """User status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"


class User(Base):
    """User model - 用户表
    
    说明：
    - 初始联赛体系会填充 AI 用户 (is_ai=True)
    - 新玩家注册时，会替换一名 AI 用户，接管其球队
    - 一个用户对应一支球队
    """
    __tablename__ = "users"
    
    # 基本信息
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(50), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # AI 用户标识 - 关键字段！
    # AI 用户是系统预填充的占位用户，新玩家注册时会替换 AI 用户
    is_ai: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    
    # VIP 系统 - 只有有和无，没有等级
    is_vip: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # 等级和经验
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # 状态
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus), 
        default=UserStatus.ACTIVE, 
        nullable=False
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # 时间戳
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # 关联关系
    team: Mapped["Team"] = relationship("Team", back_populates="user", uselist=False)
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, is_ai={self.is_ai}, is_vip={self.is_vip})>"

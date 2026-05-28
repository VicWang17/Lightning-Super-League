"""
Mail model - 游戏内邮件/通知系统
"""
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Text, Enum, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class MailCategory(str, enum.Enum):
    """邮件分类"""
    MATCH_PREVIEW = "match_preview"      # 比赛预告
    MATCH_RESULT = "match_result"        # 比赛结果
    SPONSOR = "sponsor"                  # 赞助商
    TRANSFER = "transfer"                # 转会
    FINANCE = "finance"                  # 财务
    SYSTEM = "system"                    # 系统通知


class MailPriority(str, enum.Enum):
    """邮件优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


MAIL_CATEGORY_LABELS = {
    MailCategory.MATCH_PREVIEW: "比赛预告",
    MailCategory.MATCH_RESULT: "比赛结果",
    MailCategory.SPONSOR: "赞助商",
    MailCategory.TRANSFER: "转会市场",
    MailCategory.FINANCE: "财务中心",
    MailCategory.SYSTEM: "系统通知",
}

MAIL_CATEGORY_ICONS = {
    MailCategory.MATCH_PREVIEW: "calendar",
    MailCategory.MATCH_RESULT: "trophy",
    MailCategory.SPONSOR: "building",
    MailCategory.TRANSFER: "transfer",
    MailCategory.FINANCE: "wallet",
    MailCategory.SYSTEM: "server",
}

MAIL_CATEGORY_COLORS = {
    MailCategory.MATCH_PREVIEW: "#0D7377",
    MailCategory.MATCH_RESULT: "#C6F135",
    MailCategory.SPONSOR: "#F59E0B",
    MailCategory.TRANSFER: "#3B82F6",
    MailCategory.FINANCE: "#10B981",
    MailCategory.SYSTEM: "#8B8BA7",
}


class Mail(Base):
    """邮件模型 - 存储发送给用户的游戏内通知"""
    __tablename__ = "mails"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    team_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    season_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("seasons.id", ondelete="SET NULL"), nullable=True, index=True)
    category: Mapped[MailCategory] = mapped_column(Enum(MailCategory), nullable=False, default=MailCategory.SYSTEM)
    priority: Mapped[MailPriority] = mapped_column(Enum(MailPriority), nullable=False, default=MailPriority.NORMAL)

    sender_name: Mapped[str] = mapped_column(String(100), nullable=False, default="系统")
    sender_avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关联数据（可选，用于跳转）
    related_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    related_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    related_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # 奖励/操作标记
    has_action: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    action_taken: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    action_label: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # 过期时间（可选）
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_mails_user_read", "user_id", "is_read"),
        Index("ix_mails_user_category", "user_id", "category"),
        Index("ix_mails_created", "created_at"),
    )

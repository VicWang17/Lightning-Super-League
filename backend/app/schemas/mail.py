"""
Mail schemas - 邮件系统 Pydantic 模型
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.base import ResponseSchema


class MailCategory(str, Enum):
    """邮件分类"""
    MATCH_PREVIEW = "match_preview"
    MATCH_RESULT = "match_result"
    SPONSOR = "sponsor"
    TRANSFER = "transfer"
    FINANCE = "finance"
    SYSTEM = "system"


class MailPriority(str, Enum):
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

MAIL_CATEGORY_COLORS = {
    MailCategory.MATCH_PREVIEW: "#0D7377",
    MailCategory.MATCH_RESULT: "#C6F135",
    MailCategory.SPONSOR: "#F59E0B",
    MailCategory.TRANSFER: "#3B82F6",
    MailCategory.FINANCE: "#10B981",
    MailCategory.SYSTEM: "#8B8BA7",
}


class MailItem(BaseModel):
    """邮件列表项"""
    id: str
    category: MailCategory
    priority: MailPriority
    sender_name: str
    sender_avatar_url: Optional[str] = None
    subject: str
    summary: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    related_id: Optional[str] = None
    related_type: Optional[str] = None
    related_url: Optional[str] = None
    has_action: bool
    action_taken: bool
    action_label: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MailDetail(MailItem):
    """邮件详情"""
    body: str


class MailListResponse(BaseModel):
    """邮件列表响应"""
    items: List[MailItem]
    total: int
    unread_count: int
    category_counts: dict = Field(default_factory=dict)


class MailCreateRequest(BaseModel):
    """创建邮件请求（内部使用）"""
    user_id: str
    category: MailCategory = MailCategory.SYSTEM
    priority: MailPriority = MailPriority.NORMAL
    sender_name: str = "系统"
    sender_avatar_url: Optional[str] = None
    subject: str
    summary: Optional[str] = None
    body: str
    related_id: Optional[str] = None
    related_type: Optional[str] = None
    related_url: Optional[str] = None
    has_action: bool = False
    action_label: Optional[str] = None
    expires_at: Optional[datetime] = None


class MarkReadRequest(BaseModel):
    """标记已读请求"""
    mail_ids: List[str]


class UnreadCountResponse(BaseModel):
    """未读数量响应"""
    total: int
    by_category: dict

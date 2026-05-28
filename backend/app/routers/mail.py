"""
Mail API routes - 邮件/通知中心接口
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update

from app.dependencies import get_db, get_current_user
from app.schemas import ResponseSchema
from app.schemas.mail import (
    MailItem,
    MailDetail,
    MailListResponse,
    MarkReadRequest,
    UnreadCountResponse,
    MailCategory,
    MAIL_CATEGORY_LABELS,
)
from app.models import Mail

router = APIRouter(prefix="/mail", tags=["邮件"])


def _mail_to_item(mail: Mail) -> MailItem:
    """将 Mail ORM 对象转换为 MailItem schema"""
    return MailItem(
        id=mail.id,
        category=MailCategory(mail.category.value),
        priority=mail.priority.value,
        sender_name=mail.sender_name,
        sender_avatar_url=mail.sender_avatar_url,
        subject=mail.subject,
        summary=mail.summary,
        is_read=mail.is_read,
        read_at=mail.read_at,
        related_id=mail.related_id,
        related_type=mail.related_type,
        related_url=mail.related_url,
        has_action=mail.has_action,
        action_taken=mail.action_taken,
        action_label=mail.action_label,
        expires_at=mail.expires_at,
        created_at=mail.created_at,
    )


@router.get(
    "/",
    response_model=ResponseSchema[MailListResponse],
    summary="获取邮件列表",
    description="获取当前用户的邮件列表，支持按分类和已读状态筛选",
)
async def list_mails(
    category: Optional[MailCategory] = Query(None, description="分类筛选"),
    is_read: Optional[bool] = Query(None, description="已读状态筛选"),
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取邮件列表"""
    user_id = current_user["user_id"]

    # 基础查询
    base_where = [Mail.user_id == user_id, Mail.deleted_at.is_(None)]
    if category:
        base_where.append(Mail.category == category)
    if is_read is not None:
        base_where.append(Mail.is_read == is_read)

    # 查询邮件列表
    stmt = (
        select(Mail)
        .where(and_(*base_where))
        .order_by(Mail.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    mails = result.scalars().all()

    # 查询总数
    count_stmt = select(func.count(Mail.id)).where(and_(*base_where))
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 查询未读总数
    unread_where = [Mail.user_id == user_id, Mail.is_read == False, Mail.deleted_at.is_(None)]
    unread_stmt = select(func.count(Mail.id)).where(and_(*unread_where))
    unread_result = await db.execute(unread_stmt)
    unread_count = unread_result.scalar() or 0

    # 按分类统计数量
    cat_stmt = (
        select(Mail.category, func.count(Mail.id))
        .where(Mail.user_id == user_id, Mail.deleted_at.is_(None))
        .group_by(Mail.category)
    )
    cat_result = await db.execute(cat_stmt)
    category_counts = {}
    for cat, cnt in cat_result.all():
        category_counts[cat.value] = cnt

    return ResponseSchema(
        success=True,
        data=MailListResponse(
            items=[_mail_to_item(m) for m in mails],
            total=total,
            unread_count=unread_count,
            category_counts=category_counts,
        ),
    )


@router.get(
    "/unread-count",
    response_model=ResponseSchema[UnreadCountResponse],
    summary="获取未读邮件数量",
)
async def get_unread_count(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取未读邮件数量"""
    user_id = current_user["user_id"]

    # 总未读
    total_stmt = select(func.count(Mail.id)).where(
        Mail.user_id == user_id,
        Mail.is_read == False,
        Mail.deleted_at.is_(None),
    )
    total_result = await db.execute(total_stmt)
    total = total_result.scalar() or 0

    # 按分类未读
    cat_stmt = (
        select(Mail.category, func.count(Mail.id))
        .where(
            Mail.user_id == user_id,
            Mail.is_read == False,
            Mail.deleted_at.is_(None),
        )
        .group_by(Mail.category)
    )
    cat_result = await db.execute(cat_stmt)
    by_category = {}
    for cat, cnt in cat_result.all():
        by_category[cat.value] = cnt

    return ResponseSchema(
        success=True,
        data=UnreadCountResponse(total=total, by_category=by_category),
    )


@router.get(
    "/{mail_id}",
    response_model=ResponseSchema[MailDetail],
    summary="获取邮件详情",
)
async def get_mail(
    mail_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取邮件详情，同时自动标记为已读"""
    user_id = current_user["user_id"]

    stmt = select(Mail).where(
        Mail.id == mail_id,
        Mail.user_id == user_id,
        Mail.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    mail = result.scalar_one_or_none()

    if not mail:
        return ResponseSchema(success=False, message="邮件不存在", data=None)

    # 自动标记为已读
    if not mail.is_read:
        from datetime import datetime
        mail.is_read = True
        mail.read_at = datetime.utcnow()
        await db.commit()

    return ResponseSchema(
        success=True,
        data=MailDetail(
            id=mail.id,
            category=MailCategory(mail.category.value),
            priority=mail.priority.value,
            sender_name=mail.sender_name,
            sender_avatar_url=mail.sender_avatar_url,
            subject=mail.subject,
            summary=mail.summary,
            body=mail.body,
            is_read=mail.is_read,
            read_at=mail.read_at,
            related_id=mail.related_id,
            related_type=mail.related_type,
            related_url=mail.related_url,
            has_action=mail.has_action,
            action_taken=mail.action_taken,
            action_label=mail.action_label,
            expires_at=mail.expires_at,
            created_at=mail.created_at,
        ),
    )


@router.post(
    "/read",
    response_model=ResponseSchema,
    summary="批量标记已读",
)
async def mark_read(
    request: MarkReadRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量标记邮件为已读"""
    user_id = current_user["user_id"]
    from datetime import datetime

    await db.execute(
        update(Mail)
        .where(
            Mail.id.in_(request.mail_ids),
            Mail.user_id == user_id,
        )
        .values(is_read=True, read_at=datetime.utcnow())
    )
    await db.commit()

    return ResponseSchema(success=True, message="标记成功")


@router.post(
    "/read-all",
    response_model=ResponseSchema,
    summary="标记全部已读",
)
async def mark_all_read(
    category: Optional[MailCategory] = Query(None, description="指定分类，不传则全部"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标记当前用户的全部邮件为已读"""
    user_id = current_user["user_id"]
    from datetime import datetime

    where_clause = [Mail.user_id == user_id, Mail.is_read == False]
    if category:
        where_clause.append(Mail.category == category)

    await db.execute(
        update(Mail)
        .where(and_(*where_clause))
        .values(is_read=True, read_at=datetime.utcnow())
    )
    await db.commit()

    return ResponseSchema(success=True, message="全部标记已读成功")

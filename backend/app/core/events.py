"""
EventQueue - 虚拟时钟事件队列（Phase 2）

所有赛季推进逻辑由事件驱动，不再使用 day-by-day 循环：
  SEASON_START          → 初始化赛季
  MATCH_DAY             → 批量执行当天所有比赛（并发）
  MATCH_ENGINE_COMPLETE → Go 引擎返回结果（未来）
  CUP_PROGRESSION       → 杯赛晋级/淘汰
  PROMOTION_RELEGATION  → 升降级处理
  SEASON_END            → 赛季结算

EventQueue 本身是无状态逻辑类；持久化由 ORM 模型承担。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, asc, update

from app.core.logging import get_logger

logger = get_logger(__name__)


class EventType(str, Enum):
    SEASON_START = "season_start"
    SEASON_END = "season_end"
    MATCH_DAY = "match_day"
    MATCH_ENGINE_COMPLETE = "match_engine_complete"
    CUP_PROGRESSION = "cup_progression"
    PROMOTION_RELEGATION = "promotion_relegation"


class EventStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class GameEvent:
    """内存中的游戏事件（与 ORM 模型映射）"""
    id: Optional[int] = None
    event_type: EventType = EventType.MATCH_DAY
    payload: Dict[str, Any] = field(default_factory=dict)
    scheduled_at: datetime = field(default_factory=datetime.utcnow)
    status: EventStatus = EventStatus.PENDING
    processed_at: Optional[datetime] = None
    error_msg: Optional[str] = None
    retry_count: int = 0
    created_at: Optional[datetime] = None

    # ------------------------------------------------------------------
    # 序列化
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "payload": self.payload,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "status": self.status.value,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "error_msg": self.error_msg,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_orm(cls, obj) -> "GameEvent":
        """从 ORM 对象构造（避免循环导入，obj 类型为 models.events.EventQueue）"""
        return cls(
            id=obj.id,
            event_type=EventType(obj.event_type),
            payload=obj.payload or {},
            scheduled_at=obj.scheduled_at,
            status=EventStatus(obj.status),
            processed_at=obj.processed_at,
            error_msg=obj.error_msg,
            retry_count=obj.retry_count or 0,
            created_at=obj.created_at,
        )


class EventQueue:
    """
    事件队列操作类（异步）
    所有方法接收 db session，不持有连接。
    """

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------
    @staticmethod
    async def push(
        db: AsyncSession,
        event_type: EventType,
        payload: Dict[str, Any],
        scheduled_at: Optional[datetime] = None,
    ) -> GameEvent:
        """推送一个新事件到队列"""
        from app.models.events import EventQueue as EventQueueModel  # 延迟导入防循环

        evt = EventQueueModel(
            event_type=event_type.value,
            payload=payload,
            scheduled_at=scheduled_at or datetime.utcnow(),
            status=EventStatus.PENDING.value,
            retry_count=0,
        )
        db.add(evt)
        await db.flush()
        await db.refresh(evt)
        logger.info(f"Event pushed: type={event_type.value}, id={evt.id}, scheduled={evt.scheduled_at}")
        return GameEvent.from_orm(evt)

    @staticmethod
    async def push_many(
        db: AsyncSession,
        events: List[GameEvent],
    ) -> List[GameEvent]:
        """批量推送事件"""
        from app.models.events import EventQueue as EventQueueModel

        orm_objs = []
        for e in events:
            orm_objs.append(
                EventQueueModel(
                    event_type=e.event_type.value,
                    payload=e.payload,
                    scheduled_at=e.scheduled_at,
                    status=EventStatus.PENDING.value,
                    retry_count=0,
                )
            )
        db.add_all(orm_objs)
        await db.flush()
        for o in orm_objs:
            await db.refresh(o)
        logger.info(f"Events pushed in batch: count={len(orm_objs)}")
        return [GameEvent.from_orm(o) for o in orm_objs]

    # ------------------------------------------------------------------
    # 读取
    # ------------------------------------------------------------------
    @staticmethod
    async def peek(
        db: AsyncSession,
        now: Optional[datetime] = None,
    ) -> Optional[GameEvent]:
        """查看下一个待处理事件（不取走）"""
        from app.models.events import EventQueue as EventQueueModel

        now = now or datetime.utcnow()
        result = await db.execute(
            select(EventQueueModel)
            .where(
                and_(
                    EventQueueModel.status == EventStatus.PENDING.value,
                    EventQueueModel.scheduled_at <= now,
                )
            )
            .order_by(asc(EventQueueModel.scheduled_at), asc(EventQueueModel.id))
            .limit(1)
        )
        obj = result.scalar_one_or_none()
        return GameEvent.from_orm(obj) if obj else None

    @staticmethod
    async def pop(
        db: AsyncSession,
        now: Optional[datetime] = None,
    ) -> Optional[GameEvent]:
        """取走下一个待处理事件，并将其状态设为 PROCESSING（乐观锁）"""
        from app.models.events import EventQueue as EventQueueModel

        now = now or datetime.utcnow()
        # 先查询
        result = await db.execute(
            select(EventQueueModel)
            .where(
                and_(
                    EventQueueModel.status == EventStatus.PENDING.value,
                    EventQueueModel.scheduled_at <= now,
                )
            )
            .order_by(asc(EventQueueModel.scheduled_at), asc(EventQueueModel.id))
            .limit(1)
            .with_for_update(skip_locked=True)  # 跳过被锁住的行，支持并发消费
        )
        obj = result.scalar_one_or_none()
        if not obj:
            return None

        # 状态迁移
        obj.status = EventStatus.PROCESSING.value
        await db.flush()
        logger.info(f"Event popped: type={obj.event_type}, id={obj.id}")
        return GameEvent.from_orm(obj)

    @staticmethod
    async def list_pending(
        db: AsyncSession,
        now: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[GameEvent]:
        """列出所有已到期的待处理事件"""
        from app.models.events import EventQueue as EventQueueModel

        now = now or datetime.utcnow()
        result = await db.execute(
            select(EventQueueModel)
            .where(
                and_(
                    EventQueueModel.status == EventStatus.PENDING.value,
                    EventQueueModel.scheduled_at <= now,
                )
            )
            .order_by(asc(EventQueueModel.scheduled_at), asc(EventQueueModel.id))
            .limit(limit)
        )
        return [GameEvent.from_orm(o) for o in result.scalars().all()]

    # ------------------------------------------------------------------
    # 状态变更
    # ------------------------------------------------------------------
    @staticmethod
    async def complete(db: AsyncSession, event_id: int) -> None:
        """标记事件完成"""
        from app.models.events import EventQueue as EventQueueModel

        await db.execute(
            update(EventQueueModel)
            .where(EventQueueModel.id == event_id)
            .values(
                status=EventStatus.COMPLETED.value,
                processed_at=datetime.utcnow(),
            )
        )
        logger.info(f"Event completed: id={event_id}")

    @staticmethod
    async def fail(
        db: AsyncSession,
        event_id: int,
        error_msg: str,
        max_retries: int = 3,
    ) -> None:
        """标记事件失败，或重新放回队列（若 retry_count < max_retries）"""
        from app.models.events import EventQueue as EventQueueModel

        result = await db.execute(
            select(EventQueueModel).where(EventQueueModel.id == event_id)
        )
        obj = result.scalar_one_or_none()
        if not obj:
            return

        obj.retry_count = (obj.retry_count or 0) + 1
        if obj.retry_count >= max_retries:
            obj.status = EventStatus.FAILED.value
            obj.error_msg = error_msg
            obj.processed_at = datetime.utcnow()
            logger.error(f"Event failed permanently: id={event_id}, error={error_msg}")
        else:
            obj.status = EventStatus.PENDING.value
            obj.error_msg = error_msg
            # 退避：每次重试延迟 5 秒
            obj.scheduled_at = datetime.utcnow() + timedelta(seconds=5 * obj.retry_count)
            logger.warning(f"Event retry scheduled: id={event_id}, retry={obj.retry_count}, error={error_msg}")

    @staticmethod
    async def cancel(db: AsyncSession, event_id: int) -> None:
        """取消事件"""
        from app.models.events import EventQueue as EventQueueModel

        await db.execute(
            update(EventQueueModel)
            .where(EventQueueModel.id == event_id)
            .values(status=EventStatus.CANCELLED.value, processed_at=datetime.utcnow())
        )
        logger.info(f"Event cancelled: id={event_id}")

    # ------------------------------------------------------------------
    # 赛季事件快速构建
    # ------------------------------------------------------------------
    @staticmethod
    def build_season_events(
        season_id: int,
        league_days: List[int],
        cup_days: List[int],
        promotion_day: int,
        total_days: int,
        start_date: datetime,
    ) -> List[GameEvent]:
        """根据赛季模板一次性生成全部赛季事件（SEASON_START + 每天 MATCH_DAY + CUP_PROGRESSION + PROMOTION_RELEGATION + SEASON_END）"""
        events: List[GameEvent] = []

        # 赛季开始
        events.append(
            GameEvent(
                event_type=EventType.SEASON_START,
                payload={"season_id": season_id, "start_date": start_date.isoformat()},
                scheduled_at=start_date,
            )
        )

        # 每天一个 MATCH_DAY 事件
        for day in range(total_days):
            scheduled = start_date + timedelta(days=day)
            payload: Dict[str, Any] = {"season_id": season_id, "day": day}
            if day in league_days:
                payload["league_round"] = league_days.index(day) + 1
            if day in cup_days:
                payload["cup_round"] = cup_days.index(day) + 1
            events.append(
                GameEvent(
                    event_type=EventType.MATCH_DAY,
                    payload=payload,
                    scheduled_at=scheduled,
                )
            )

        # 杯赛晋级事件（每个杯赛日之后）
        for cup_day in cup_days:
            scheduled = start_date + timedelta(days=cup_day + 1)
            events.append(
                GameEvent(
                    event_type=EventType.CUP_PROGRESSION,
                    payload={"season_id": season_id, "after_day": cup_day},
                    scheduled_at=scheduled,
                )
            )

        # 升降级
        if promotion_day > 0:
            scheduled = start_date + timedelta(days=promotion_day)
            events.append(
                GameEvent(
                    event_type=EventType.PROMOTION_RELEGATION,
                    payload={"season_id": season_id, "day": promotion_day},
                    scheduled_at=scheduled,
                )
            )

        # 赛季结束
        end_date = start_date + timedelta(days=total_days)
        events.append(
            GameEvent(
                event_type=EventType.SEASON_END,
                payload={"season_id": season_id, "end_date": end_date.isoformat()},
                scheduled_at=end_date,
            )
        )

        return events

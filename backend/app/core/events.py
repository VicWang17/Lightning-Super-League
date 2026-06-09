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
from app.core.formats import get_default_format

logger = get_logger(__name__)


class EventType(str, Enum):
    SEASON_START = "season_start"
    SEASON_END = "season_end"
    MATCH_DAY = "match_day"
    MATCH_ENGINE_COMPLETE = "match_engine_complete"
    CUP_PROGRESSION = "cup_progression"
    PROMOTION_RELEGATION = "promotion_relegation"
    # Economy events (Phase 2)
    SEASON_FINANCE_INITIALIZED = "season_finance_initialized"
    MATCH_FINANCE_SETTLED = "match_finance_settled"
    WAGES_PAID = "wages_paid"
    SEASON_FINANCE_CLOSED = "season_finance_closed"
    # Budget / Sponsor events (Phase 3)
    BUDGET_WINDOW_OPENED = "budget_window_opened"
    BUDGET_WINDOW_CLOSED = "budget_window_closed"
    # Youth Academy events (Phase 3)
    YOUTH_REFRESH = "youth_refresh"
    YOUTH_TRAINING = "youth_training"
    # Training events
    TRAINING_DAY = "training_day"
    # Reminder events (Phase 7: 邮件提醒系统)
    MATCH_PREVIEW_REMINDER = "match_preview_reminder"
    TACTICS_REMINDER = "tactics_reminder"
    TRAINING_REMINDER = "training_reminder"
    # Draft events (Phase 4)
    DRAFT_PREFERENCES_OPEN = "draft_preferences_open"
    DRAFT_RUN = "draft_run"
    DRAFT_SIGNING_EXPIRE = "draft_signing_expire"
    # Transfer market events (Phase 6)
    TRANSFER_OFFER_EXPIRES = "transfer_offer_expires"
    TRANSFER_LISTING_DEADLINE = "transfer_listing_deadline"
    AI_TRANSFER_MARKET_SCAN = "ai_transfer_market_scan"
    AI_TRANSFER_OFFER_RESPONSE = "ai_transfer_offer_response"


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
        logger.info(f"Event pushed: type={event_type.value}, id={evt.id}, scheduled={evt.scheduled_at}")
        return GameEvent.from_orm(evt)

    @staticmethod
    def add_pending(
        db: AsyncSession,
        event_type: EventType,
        payload: Dict[str, Any],
        scheduled_at: Optional[datetime] = None,
    ) -> None:
        """添加待处理事件，但不立即 flush。

        用于业务流程内批量附带创建事件，避免每插入一个事件都刷新
        event_queues，降低长事务里的锁竞争。
        """
        from app.models.events import EventQueue as EventQueueModel

        db.add(
            EventQueueModel(
                event_type=event_type.value,
                payload=payload,
                scheduled_at=scheduled_at or datetime.utcnow(),
                status=EventStatus.PENDING.value,
                retry_count=0,
            )
        )

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
        wage_days: Optional[List[int]] = None,
    ) -> List[GameEvent]:
        """根据赛季模板一次性生成小时级赛季事件。

        业务日从 1 开始；scheduled_at 才是定时任务的精确触发时间。
        """
        template = get_default_format().season
        events: List[GameEvent] = []

        def at_day_hour(day: int, hour: int, minute: int = 0, second: int = 0) -> datetime:
            if day < 1:
                raise ValueError(f"season day must be >= 1, got {day}")
            return (start_date + timedelta(days=day - 1)).replace(
                hour=hour, minute=minute, second=second, microsecond=0
            )

        # 赛季开始
        events.append(
            GameEvent(
                event_type=EventType.SEASON_START,
                payload={"season_id": season_id, "start_date": start_date.isoformat()},
                scheduled_at=at_day_hour(1, template.season_start_hour),
            )
        )

        # 赛季财务初始化（Day 1）
        events.append(
            GameEvent(
                event_type=EventType.SEASON_FINANCE_INITIALIZED,
                payload={"season_id": season_id, "day": 1},
                scheduled_at=at_day_hour(1, template.finance_initialization_hour),
            )
        )

        # 每天一个 MATCH_DAY 事件 + TRAINING_DAY（赛后训练结算）+ 提醒事件
        for day in range(1, total_days + 1):
            payload: Dict[str, Any] = {"season_id": season_id, "day": day}
            if day in league_days:
                payload["league_round"] = league_days.index(day) + 1
            if day in cup_days:
                payload["cup_round"] = cup_days.index(day) + 1

            has_match = day in league_days or day in cup_days

            # 早上 8:00：比赛预告提醒（仅比赛日）
            if has_match:
                events.append(
                    GameEvent(
                        event_type=EventType.MATCH_PREVIEW_REMINDER,
                        payload={"season_id": season_id, "day": day},
                        scheduled_at=at_day_hour(day, template.match_preview_reminder_hour),
                    )
                )
                # 中午 12:00：战术设置提醒（仅比赛日）
                events.append(
                    GameEvent(
                        event_type=EventType.TACTICS_REMINDER,
                        payload={"season_id": season_id, "day": day},
                        scheduled_at=at_day_hour(day, template.tactics_reminder_hour),
                    )
                )

            # 早上 8:00：训练提醒（每天）
            events.append(
                GameEvent(
                    event_type=EventType.TRAINING_REMINDER,
                    payload={"season_id": season_id, "day": day},
                    scheduled_at=at_day_hour(day, template.training_reminder_hour),
                )
            )

            events.append(
                GameEvent(
                    event_type=EventType.MATCH_DAY,
                    payload=payload,
                    scheduled_at=at_day_hour(day, template.kickoff_hour),
                )
            )
            # 训练安排在比赛后 2 小时
            events.append(
                GameEvent(
                    event_type=EventType.TRAINING_DAY,
                    payload={"season_id": season_id, "day": day},
                    scheduled_at=at_day_hour(day, template.kickoff_hour + 2),
                )
            )
            # AI 转会扫描安排在每日训练结算之后，确保最新状态/疲劳/成长已写入。
            events.append(
                GameEvent(
                    event_type=EventType.AI_TRANSFER_MARKET_SCAN,
                    payload={"season_id": season_id, "day": day},
                    scheduled_at=at_day_hour(day, template.kickoff_hour + 3),
                )
            )

        # 杯赛晋级事件（杯赛日比赛结束后）
        for cup_day in cup_days:
            events.append(
                GameEvent(
                    event_type=EventType.CUP_PROGRESSION,
                    payload={"season_id": season_id, "after_day": cup_day},
                    scheduled_at=at_day_hour(cup_day, template.cup_progression_hour),
                )
            )

        # 升降级
        promotion_days = getattr(template, "promotion_event_days", (promotion_day,))
        for event_day in promotion_days:
            if event_day <= 0 or event_day > total_days:
                continue
            events.append(
                GameEvent(
                    event_type=EventType.PROMOTION_RELEGATION,
                    payload={"season_id": season_id, "day": event_day},
                    scheduled_at=at_day_hour(event_day, template.promotion_hour),
                )
            )

        # 工资发放事件（Phase 2 经济系统）
        for wage_day in (wage_days or []):
            if wage_day <= total_days:
                events.append(
                    GameEvent(
                        event_type=EventType.WAGES_PAID,
                        payload={"season_id": season_id, "day": wage_day, "period_key": f"wage_{wage_day}"},
                        scheduled_at=at_day_hour(wage_day, template.wage_hour),
                    )
                )

        # Phase 3: 青训刷新事件
        for refresh_day in template.youth_refresh_days:
            if refresh_day <= total_days:
                events.append(
                    GameEvent(
                        event_type=EventType.YOUTH_REFRESH,
                        payload={"season_id": season_id, "day": refresh_day},
                        scheduled_at=at_day_hour(refresh_day, template.youth_refresh_hour),
                    )
                )

        # Phase 3: 青训训练事件（每 training_interval_days 天一次）
        for train_day in range(1, total_days + 1):
            if train_day % template.youth_training_interval_days == 0:
                events.append(
                    GameEvent(
                        event_type=EventType.YOUTH_TRAINING,
                        payload={"season_id": season_id, "day": train_day},
                        scheduled_at=at_day_hour(train_day, template.youth_training_hour),
                    )
                )

        # Phase 3: 预算窗口事件（赛季中后期）
        budget_open_day = max(1, total_days - 10)
        budget_close_day = max(1, total_days - 5)
        events.append(
            GameEvent(
                event_type=EventType.BUDGET_WINDOW_OPENED,
                payload={"season_id": season_id, "day": budget_open_day},
                scheduled_at=at_day_hour(budget_open_day, template.budget_open_hour),
            )
        )
        events.append(
            GameEvent(
                event_type=EventType.BUDGET_WINDOW_CLOSED,
                payload={"season_id": season_id, "day": budget_close_day},
                scheduled_at=at_day_hour(budget_close_day, template.budget_close_hour),
            )
        )

        # Phase 4: 选秀事件已移除（简化闭环设计文档）
        # 保留 EventType 枚举值以避免数据库已有事件报错

        # 赛季结束 + 财务结算
        end_date = at_day_hour(total_days, template.season_end_hour)
        events.append(
            GameEvent(
                event_type=EventType.SEASON_FINANCE_CLOSED,
                payload={"season_id": season_id, "end_date": end_date.isoformat()},
                scheduled_at=at_day_hour(total_days, template.season_finance_close_hour),
            )
        )

        # 赛季结束（原有系统事件，放在财务结算之后）
        events.append(
            GameEvent(
                event_type=EventType.SEASON_END,
                payload={"season_id": season_id, "end_date": end_date.isoformat()},
                scheduled_at=end_date,
            )
        )

        return sorted(events, key=lambda event: event.scheduled_at)

"""
Dev Console API - 开发调试控制台（Phase 4）

⚠️ 仅限开发环境使用，不应暴露到生产环境。
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.core.clock import clock, GameClock
from app.core.events import EventQueue, EventStatus, GameEvent, EventType
from app.schemas import ResponseSchema
from app.services.season_service import SeasonService
from app.models.season import Season, SeasonStatus
from sqlalchemy import select, desc, asc

router = APIRouter(prefix="/dev", tags=["开发调试"])


# =================================================================
# Schemas
# =================================================================
class ClockStatusResponse(BaseModel):
    mode: str
    virtual_now: datetime
    speed: float


class ClockTickRequest(BaseModel):
    steps: int = 1


class ClockFastForwardRequest(BaseModel):
    days: Optional[int] = None
    events: Optional[int] = None


class EventListItem(BaseModel):
    id: int
    event_type: str
    payload: dict
    scheduled_at: datetime
    status: str
    processed_at: Optional[datetime]
    retry_count: int


class SeasonAdvanceRequest(BaseModel):
    days: int = 1


# =================================================================
# Clock APIs
# =================================================================
@router.get("/clock", response_model=ResponseSchema[ClockStatusResponse])
async def get_clock_status():
    """查看 GameClock 当前状态"""
    return ResponseSchema(data=ClockStatusResponse(
        mode=clock.mode,
        virtual_now=clock.now(),
        speed=clock.speed,
    ))


@router.post("/clock/tick", response_model=ResponseSchema[dict])
async def clock_tick(req: ClockTickRequest, db: AsyncSession = Depends(get_db)):
    """单步推进时钟：处理下一个事件"""
    service = SeasonService(db)
    results = []
    for _ in range(req.steps):
        result = await service.process_next_event()
        if result is None:
            break
        results.append(result)
    return ResponseSchema(data={"processed": len(results), "results": results})


@router.post("/clock/fast-forward", response_model=ResponseSchema[dict])
async def clock_fast_forward(req: ClockFastForwardRequest, db: AsyncSession = Depends(get_db)):
    """快进时钟：按事件数或天数推进"""
    service = SeasonService(db)
    results = []
    
    if req.events:
        for _ in range(req.events):
            result = await service.process_next_event()
            if result is None:
                break
            results.append(result)
    elif req.days:
        result = await db.execute(
            select(Season).where(Season.status == SeasonStatus.ONGOING).order_by(desc(Season.season_number))
        )
        season = result.scalar_one_or_none()
        if not season:
            raise HTTPException(status_code=400, detail="No ongoing season")
        results = await service.fast_forward(season.current_day + req.days, season)
    else:
        raise HTTPException(status_code=400, detail="Must specify 'days' or 'events'")
    
    return ResponseSchema(data={"processed": len(results), "results": results})


@router.post("/clock/set-mode", response_model=ResponseSchema[dict])
async def set_clock_mode(mode: str, speed: Optional[float] = None):
    """设置时钟模式（realtime / turbo / step / paused）"""
    if mode not in ("realtime", "turbo", "step", "paused"):
        raise HTTPException(status_code=400, detail="Invalid mode")
    clock.set_mode(mode)
    if speed is not None and mode == "turbo":
        clock.speed = max(1.0, speed)
    return ResponseSchema(data={"mode": clock.mode, "speed": clock.speed})


# =================================================================
# EventQueue APIs
# =================================================================
@router.get("/events", response_model=ResponseSchema[List[EventListItem]])
async def list_events(
    status: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """查看 EventQueue 列表（支持筛选和分页）"""
    from app.models.events import EventQueue as EventQueueModel
    
    query = select(EventQueueModel).order_by(asc(EventQueueModel.scheduled_at), asc(EventQueueModel.id))
    if status:
        query = query.where(EventQueueModel.status == status)
    if event_type:
        query = query.where(EventQueueModel.event_type == event_type)
    
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    items = []
    for obj in result.scalars().all():
        items.append(EventListItem(
            id=obj.id,
            event_type=obj.event_type,
            payload=obj.payload or {},
            scheduled_at=obj.scheduled_at,
            status=obj.status,
            processed_at=obj.processed_at,
            retry_count=obj.retry_count or 0,
        ))
    return ResponseSchema(data=items)


@router.post("/events/{event_id}/retry", response_model=ResponseSchema[dict])
async def retry_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """手动重试失败事件"""
    from app.models.events import EventQueue as EventQueueModel
    
    result = await db.execute(select(EventQueueModel).where(EventQueueModel.id == event_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Event not found")
    if obj.status != EventStatus.FAILED.value:
        raise HTTPException(status_code=400, detail="Only failed events can be retried")
    
    obj.status = EventStatus.PENDING.value
    obj.retry_count = 0
    obj.error_msg = None
    obj.scheduled_at = datetime.utcnow()
    await db.commit()
    
    return ResponseSchema(data={"event_id": event_id, "status": "pending"})


@router.delete("/events/{event_id}", response_model=ResponseSchema[dict])
async def cancel_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """取消一个待处理事件"""
    await EventQueue.cancel(db, event_id)
    return ResponseSchema(data={"event_id": event_id, "status": "cancelled"})


# =================================================================
# Season APIs
# =================================================================
@router.post("/season/advance", response_model=ResponseSchema[dict])
async def season_advance(req: SeasonAdvanceRequest, db: AsyncSession = Depends(get_db)):
    """推进赛季 N 天"""
    service = SeasonService(db)
    result = await db.execute(
        select(Season).where(Season.status == SeasonStatus.ONGOING).order_by(desc(Season.season_number))
    )
    season = result.scalar_one_or_none()
    if not season:
        raise HTTPException(status_code=400, detail="No ongoing season")
    
    results = []
    for _ in range(req.days):
        day_result = await service.process_next_day(season)
        results.append(day_result)
        if day_result.get("event") == "season_end":
            break
        await db.refresh(season)
    
    return ResponseSchema(data={"days": len(results), "results": results})

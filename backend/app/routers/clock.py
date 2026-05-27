"""
GameClock 公开路由 - 前端虚拟时钟显示

无需认证，任何用户都可查询当前游戏时间。
"""
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas import ResponseSchema
from app.services.game_clock_state import GameClockStateService

router = APIRouter(prefix="/clock", tags=["时钟"])


class ClockStatusResponse(BaseModel):
    mode: str
    virtual_now: datetime
    speed: float


@router.get("", response_model=ResponseSchema[ClockStatusResponse])
async def get_clock_status(db: AsyncSession = Depends(get_db)):
    """获取当前虚拟时钟状态

    前端用此接口初始化时钟显示，之后根据 mode 在本地推算：
      - realtime: 虚拟时间 ≈ 系统时间，可本地递增
      - turbo:    虚拟时间以 speed 倍速流逝
      - step:     时间不自动前进，等待手动 tick
      - paused:   时间冻结
    """
    status = await GameClockStateService(db).status()
    return ResponseSchema(data=ClockStatusResponse(
        mode=status["mode"],
        virtual_now=datetime.fromisoformat(status["virtual_now"]),
        speed=status["speed"],
    ))

"""
GameClock 公开路由 - 前端虚拟时钟显示

无需认证，任何用户都可查询当前游戏时间。
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.clock import clock
from app.schemas import ResponseSchema

router = APIRouter(prefix="/clock", tags=["时钟"])


class ClockStatusResponse(BaseModel):
    mode: str
    virtual_now: datetime
    speed: float


@router.get("", response_model=ResponseSchema[ClockStatusResponse])
async def get_clock_status():
    """获取当前虚拟时钟状态

    前端用此接口初始化时钟显示，之后根据 mode 在本地推算：
      - realtime: 虚拟时间 ≈ 系统时间，可本地递增
      - turbo:    虚拟时间以 speed 倍速流逝
      - step:     时间不自动前进，等待手动 tick
      - paused:   时间冻结
    """
    return ResponseSchema(data=ClockStatusResponse(
        mode=clock.mode,
        virtual_now=clock.now(),
        speed=clock.speed,
    ))

"""
GameClock - 全局虚拟时钟系统

用于控制游戏世界的时间流逝。开发阶段支持加速/单步/暂停模式，
线上环境退化为真实系统时间。

模式:
- realtime: 虚拟时间 = 系统时间（线上默认）
- turbo:    虚拟时间以 N 倍速推进（开发常用）
- step:     时间不自动推进，需手动 tick（调试）
- paused:   时间冻结

用法:
    from app.core.clock import clock
    now = clock.now()
    clock.advance_to(target_datetime)
"""
import os
from datetime import datetime, timedelta
from typing import Literal, Optional, List
from dataclasses import dataclass, field


ClockMode = Literal["realtime", "turbo", "step", "paused"]


@dataclass
class GameEventStub:
    """时钟内部使用的极简事件引用（完整定义在 event_queue 中）"""
    trigger_at: datetime
    event_type: str
    payload: dict = field(default_factory=dict)


class GameClock:
    """虚拟时钟控制器"""

    def __init__(
        self,
        mode: ClockMode = "realtime",
        speed: float = 1.0,
        start_time: Optional[datetime] = None,
    ):
        self.mode = mode
        self.speed = max(0.0, speed)

        # 虚拟时间的锚点
        self._virtual_now: datetime = start_time or datetime.utcnow()
        self._real_anchor: datetime = datetime.utcnow()
        self._paused_at: Optional[datetime] = None

    # ------------------------------------------------------------------
    # 核心时间读取
    # ------------------------------------------------------------------
    def now(self) -> datetime:
        """返回当前虚拟时间"""
        if self.mode == "realtime":
            return datetime.utcnow()

        if self.mode == "paused":
            return self._virtual_now

        if self.mode == "step":
            return self._virtual_now

        if self.mode == "turbo":
            real_elapsed = datetime.utcnow() - self._real_anchor
            virtual_elapsed = real_elapsed * self.speed
            return self._virtual_now + virtual_elapsed

        return datetime.utcnow()

    # ------------------------------------------------------------------
    # 推进控制
    # ------------------------------------------------------------------
    def tick(self, delta: timedelta) -> None:
        """手动推进虚拟时间（step / paused / turbo 均可）"""
        if delta.total_seconds() <= 0:
            raise ValueError("tick delta must be positive")
        self._virtual_now += delta
        self._reset_anchor()

    def advance_to(self, target: datetime) -> None:
        """将虚拟时间推进到指定目标"""
        if target < self.now():
            return
        self._virtual_now = target
        self._reset_anchor()

    def fast_forward(self, delta: timedelta) -> None:
        """快进指定时长"""
        self._virtual_now = self.now() + delta
        self._reset_anchor()

    def fast_forward_to(self, target: datetime) -> None:
        """快进直到目标时间"""
        if target < self.now():
            raise ValueError("target must be in the future")
        self._virtual_now = target
        self._reset_anchor()

    # ------------------------------------------------------------------
    # 模式切换
    # ------------------------------------------------------------------
    def set_mode(self, mode: ClockMode, speed: Optional[float] = None) -> None:
        """切换时钟模式，自动校正锚点避免时间跳跃"""
        if self.mode == mode and (speed is None or self.speed == speed):
            return

        # 切模式前，把当前虚拟时间固定下来
        self._virtual_now = self.now()
        self._reset_anchor()

        self.mode = mode
        if speed is not None:
            self.speed = max(0.0, speed)

    def pause(self) -> None:
        """暂停时钟"""
        if self.mode != "paused":
            self._virtual_now = self.now()
            self._paused_at = datetime.utcnow()
            self.mode = "paused"

    def resume(self) -> None:
        """恢复为之前模式（turbo/realtime）"""
        if self.mode == "paused":
            self._reset_anchor()
            # 默认恢复为 turbo，如果没有设置过则 realtime
            self.mode = "turbo" if self.speed > 1.0 else "realtime"

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------
    def _reset_anchor(self) -> None:
        """重新对齐真实时间锚点"""
        self._real_anchor = datetime.utcnow()
        self._paused_at = None

    def status(self) -> dict:
        return {
            "mode": self.mode,
            "speed": self.speed,
            "virtual_now": self.now().isoformat(),
            "anchor": self._real_anchor.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<GameClock mode={self.mode} speed={self.speed}x now={self.now()}>"


# ----------------------------------------------------------------------
# 全局单例（按环境变量初始化）
# ----------------------------------------------------------------------
def _create_clock_from_env() -> GameClock:
    mode = os.getenv("GAME_CLOCK_MODE", "realtime")
    speed = float(os.getenv("GAME_CLOCK_SPEED", "1.0"))
    start_iso = os.getenv("GAME_CLOCK_START")

    start_time = datetime.fromisoformat(start_iso) if start_iso else None

    if mode not in ("realtime", "turbo", "step", "paused"):
        mode = "realtime"

    return GameClock(mode=mode, speed=speed, start_time=start_time)


# 全局时钟实例
clock: GameClock = _create_clock_from_env()

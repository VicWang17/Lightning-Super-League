"""
GameClock 单元测试 - Phase 5

测试覆盖：
  • 模式切换（realtime / turbo / step / paused）
  • 时间流逝计算
  • fast_forward / tick / run_until_next_event
  • 边界条件（暂停中 tick、负速度）
"""
import pytest
from datetime import datetime, timedelta

from app.core.clock import GameClock, clock


class TestGameClock:
    """GameClock 核心测试"""
    
    def test_realtime_mode_returns_actual_time(self):
        """realtime 模式应返回真实系统时间"""
        gc = GameClock(mode="realtime")
        before = datetime.utcnow()
        now = gc.now()
        after = datetime.utcnow()
        assert before <= now <= after
    
    def test_paused_mode_freezes_time(self):
        """paused 模式应冻结虚拟时间"""
        base = datetime(2025, 1, 1, 12, 0, 0)
        gc = GameClock(mode="paused", start_time=base)
        t1 = gc.now()
        # 即使真实时间流逝，虚拟时间也应不变
        import time
        time.sleep(0.01)
        t2 = gc.now()
        assert t1 == t2 == base
    
    def test_turbo_mode_accelerates_time(self):
        """turbo 模式应按 speed 倍数加速"""
        base = datetime(2025, 1, 1, 12, 0, 0)
        gc = GameClock(mode="turbo", speed=100.0, start_time=base)
        t1 = gc.now()
        import time
        time.sleep(0.1)  # 真实 0.1s ≈ 虚拟 10s (speed=100)
        t2 = gc.now()
        elapsed = (t2 - t1).total_seconds()
        assert 8 <= elapsed <= 15  # 允许一定误差
    
    def test_step_mode_advances_on_tick(self):
        """step 模式仅在 tick 时前进"""
        base = datetime(2025, 1, 1, 12, 0, 0)
        gc = GameClock(mode="step", start_time=base)
        assert gc.now() == base
        gc.tick(timedelta(days=1))
        assert gc.now() == base + timedelta(days=1)
        gc.tick(timedelta(hours=12))
        assert gc.now() == base + timedelta(days=1, hours=12)
    
    def test_fast_forward_jumps_to_target(self):
        """fast_forward 应直接跳到目标时间"""
        base = datetime(2025, 1, 1, 12, 0, 0)
        target = datetime(2025, 6, 15, 0, 0, 0)
        gc = GameClock(mode="step", start_time=base)
        gc.fast_forward_to(target)
        assert gc.now() == target
    
    def test_mode_switch_preserves_time(self):
        """模式切换时应保持当前虚拟时间（允许 turbo 模式下几毫秒误差）"""
        base = datetime(2025, 1, 1, 12, 0, 0)
        gc = GameClock(mode="step", start_time=base)
        gc.tick(timedelta(days=5))
        current = gc.now()
        gc.set_mode("paused")
        assert gc.now() == current
        gc.set_mode("turbo")
        # turbo 依赖实时计算，允许 50ms 以内误差
        assert abs((gc.now() - current).total_seconds()) < 0.05
    
    def test_negative_tick_raises_error(self):
        """负时间 tick 应报错"""
        gc = GameClock(mode="step")
        with pytest.raises(ValueError, match="must be positive"):
            gc.tick(timedelta(seconds=-1))
    
    def test_global_clock_singleton(self):
        """全局 clock 单例应可被修改"""
        original_mode = clock.mode
        clock.set_mode("step")
        assert clock.mode == "step"
        clock.set_mode(original_mode)
        assert clock.mode == original_mode

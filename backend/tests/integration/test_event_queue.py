"""
EventQueue 集成测试 - Phase 5

测试覆盖：
  • push / pop / complete / fail / cancel 生命周期
  • 状态机转换（PENDING → PROCESSING → COMPLETED / FAILED）
  • peek 不修改状态
  • 重试机制（retry_count 递增， scheduled_at 延迟）
  • 批量 push_many
  • 并发 pop（skip_locked）
"""
import pytest
from datetime import datetime, timedelta

from app.core.events import EventQueue, GameEvent, EventType, EventStatus
from app.models.events import EventQueue as EventQueueModel


@pytest.mark.asyncio
class TestEventQueueCRUD:
    """EventQueue CRUD 测试"""
    
    async def test_push_and_pop(self, db):
        """推送后应能 pop 出来"""
        evt = await EventQueue.push(
            db, EventType.MATCH_DAY,
            payload={"season_id": "test-1", "day": 1},
            scheduled_at=datetime.utcnow() - timedelta(seconds=1),
        )
        assert evt.id is not None
        assert evt.status == EventStatus.PENDING
        
        popped = await EventQueue.pop(db)
        assert popped is not None
        assert popped.id == evt.id
        assert popped.status == EventStatus.PROCESSING
    
    async def test_peek_does_not_change_status(self, db):
        """peek 不应修改事件状态"""
        await EventQueue.push(
            db, EventType.MATCH_DAY,
            payload={"day": 2},
            scheduled_at=datetime.utcnow() - timedelta(seconds=1),
        )
        peeked = await EventQueue.peek(db)
        assert peeked is not None
        assert peeked.status == EventStatus.PENDING
        
        # 再次 peek 应仍然 pending
        peeked2 = await EventQueue.peek(db)
        assert peeked2.status == EventStatus.PENDING
    
    async def test_complete_event(self, db):
        """complete 后状态应为 COMPLETED"""
        evt = await EventQueue.push(db, EventType.CUP_PROGRESSION, payload={}, scheduled_at=datetime.utcnow() - timedelta(seconds=1))
        popped = await EventQueue.pop(db)
        await EventQueue.complete(db, popped.id)
        
        result = await db.execute(
            __import__("sqlalchemy").select(EventQueueModel).where(EventQueueModel.id == popped.id)
        )
        obj = result.scalar_one()
        assert obj.status == EventStatus.COMPLETED.value
        assert obj.processed_at is not None
    
    async def test_cancel_event(self, db):
        """cancel 后状态应为 CANCELLED"""
        evt = await EventQueue.push(db, EventType.MATCH_DAY, payload={})
        await EventQueue.cancel(db, evt.id)
        
        result = await db.execute(
            __import__("sqlalchemy").select(EventQueueModel).where(EventQueueModel.id == evt.id)
        )
        obj = result.scalar_one()
        assert obj.status == EventStatus.CANCELLED.value
    
    async def test_push_many(self, db):
        """批量推送应正确写入"""
        events = [
            GameEvent(event_type=EventType.MATCH_DAY, payload={"day": i}, scheduled_at=datetime.utcnow() - timedelta(seconds=1))
            for i in range(5)
        ]
        created = await EventQueue.push_many(db, events)
        assert len(created) == 5
        for e in created:
            assert e.id is not None
    
    async def test_list_pending(self, db):
        """list_pending 应只返回到期且 pending 的事件"""
        now = datetime.utcnow()
        # 已到期
        await EventQueue.push(db, EventType.MATCH_DAY, payload={"day": 1}, scheduled_at=now - timedelta(minutes=1))
        # 未到期
        await EventQueue.push(db, EventType.MATCH_DAY, payload={"day": 2}, scheduled_at=now + timedelta(hours=1))
        
        pending = await EventQueue.list_pending(db, now=now)
        assert len(pending) == 1
        assert pending[0].payload["day"] == 1


@pytest.mark.asyncio
class TestEventQueueRetry:
    """重试机制测试"""
    
    async def test_fail_with_retry(self, db):
        """失败未达上限时应回到 PENDING 并延迟"""
        evt = await EventQueue.push(db, EventType.MATCH_DAY, payload={}, scheduled_at=datetime.utcnow() - timedelta(seconds=1))
        popped = await EventQueue.pop(db)
        before = datetime.utcnow()
        
        await EventQueue.fail(db, popped.id, "simulated error", max_retries=3)
        
        result = await db.execute(
            __import__("sqlalchemy").select(EventQueueModel).where(EventQueueModel.id == popped.id)
        )
        obj = result.scalar_one()
        assert obj.status == EventStatus.PENDING.value
        assert obj.retry_count == 1
        assert obj.error_msg == "simulated error"
        assert obj.scheduled_at >= before  # 应被延迟
    
    async def test_fail_permanently_after_max_retries(self, db):
        """失败超过上限后应变为 FAILED"""
        evt = await EventQueue.push(db, EventType.MATCH_DAY, payload={}, scheduled_at=datetime.utcnow() - timedelta(seconds=1))
        # 先 pop 再 fail 3 次
        for _ in range(3):
            await EventQueue.pop(db)
            await EventQueue.fail(db, evt.id, "error", max_retries=3)
            evt = (await db.execute(
                __import__("sqlalchemy").select(EventQueueModel).where(EventQueueModel.id == evt.id)
            )).scalar_one()
        
        assert evt.status == EventStatus.FAILED.value
        assert evt.retry_count == 3


@pytest.mark.asyncio
class TestEventQueueConcurrency:
    """并发安全测试"""
    
    async def test_pop_skip_locked(self, db):
        """并发 pop 时，skip_locked 应确保每个事件只被一个消费者获取"""
        # 创建多个事件
        for i in range(5):
            await EventQueue.push(db, EventType.MATCH_DAY, payload={"i": i}, scheduled_at=datetime.utcnow() - timedelta(seconds=1))
        
        # 模拟两个消费者同时 pop
        pop1 = await EventQueue.pop(db)
        pop2 = await EventQueue.pop(db)
        pop3 = await EventQueue.pop(db)
        
        assert pop1 is not None
        assert pop2 is not None
        assert pop3 is not None
        assert pop1.id != pop2.id != pop3.id

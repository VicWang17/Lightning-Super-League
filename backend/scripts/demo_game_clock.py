"""
GameClock + EventQueue 从零开始演示脚本

用法:
    cd backend
    PYTHONPATH=$(pwd) python scripts/demo_game_clock.py

前提:
    MySQL 容器在运行，且数据库中已有 ONGOING 赛季（运行过 init_system.py）
"""
import asyncio
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func, desc, delete

from app.config import get_settings
from app.core.clock import clock
from app.core.events import EventQueue, EventType, EventStatus
from app.services.season_service import SeasonService
from app.models.season import Season, SeasonStatus, Fixture, FixtureStatus
from app.models.events import EventQueue as EventQueueModel

settings = get_settings()


async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("🕐 GameClock + EventQueue 演示")
        print("=" * 60)

        # 1. 时钟状态
        print("\n📍 Step 1: 当前时钟状态")
        print(f"   模式: {clock.mode}, 速度: {clock.speed}x")
        print(f"   虚拟时间: {clock.now()}")

        # 2. 切换到 step 模式
        print("\n📍 Step 2: 切换到 step 模式")
        clock.set_mode("step")
        print(f"   ✅ 已切换为 {clock.mode} 模式")

        # 3. 获取当前赛季
        print("\n📍 Step 3: 获取当前赛季")
        result = await db.execute(
            select(Season)
            .where(Season.status == SeasonStatus.ONGOING)
            .order_by(desc(Season.season_number))
            .limit(1)
        )
        season = result.scalar_one_or_none()
        if not season:
            print("   ❌ 没有找到 ONGOING 赛季，请先运行 init_system.py")
            return
        print(f"   第 {season.season_number} 赛季, 天数: {season.current_day}/{season.total_days}")

        # 4. 清理旧演示事件并创建新事件
        print("\n📍 Step 4: 创建演示事件")
        # 删除旧的 demo 事件
        await db.execute(
            delete(EventQueueModel)
            .where(EventQueueModel.payload.contains({"season_id": season.id}))
            .where(EventQueueModel.payload.contains({"demo": True}))
        )
        await db.commit()

        # 创建 3 个 MATCH_DAY 事件（scheduled 已到期，确保 pop 能拿到）
        now = clock.now()
        for i in range(3):
            day = season.current_day + 1 + i
            await EventQueue.push(
                db,
                EventType.MATCH_DAY,
                payload={"season_id": season.id, "day": day, "demo": True},
                scheduled_at=now - timedelta(seconds=10 - i),  # 已到期，按顺序
            )
        await db.commit()  # 确保写入可见

        # 重新查询确认
        result = await db.execute(
            select(EventQueueModel)
            .where(EventQueueModel.payload.contains({"demo": True}))
            .order_by(EventQueueModel.id)
        )
        events = result.scalars().all()
        print(f"   创建了 {len(events)} 个 MATCH_DAY 事件")

        # 5. 单步推进
        print("\n📍 Step 5: 单步推进（处理 3 个事件）")
        service = SeasonService(db)

        for i in range(3):
            evt = await EventQueue.peek(db)
            if not evt:
                print("   没有更多事件")
                break
            print(f"\n   → 下一个事件: {evt.event_type.value} (day={evt.payload.get('day')}, id={evt.id})")

            result = await service.process_next_event()
            if result is None:
                print("     ⚠️ process_next_event 返回 None（可能被其他消费者取走）")
                continue

            print(f"     ✅ 已处理: {result['event']}, day={result.get('season_day')}, "
                  f"比赛={result.get('fixtures_processed', 0)} 场")
            if result.get('results'):
                for r in result['results'][:2]:
                    print(f"        ⚽ {r['home_score']} - {r['away_score']}")

        await db.refresh(season)
        print(f"\n   赛季当前天数: {season.current_day}")

        # 6. 快进
        print("\n📍 Step 6: 快进（fast_forward 到 day + 2）")
        before = season.current_day
        results = await service.fast_forward(season.current_day + 2, season)
        await db.refresh(season)
        print(f"   处理了 {len(results)} 个事件, 天数: {before} → {season.current_day}")

        # 7. 比赛统计
        print("\n📍 Step 7: 比赛统计")
        result = await db.execute(
            select(func.count()).select_from(Fixture)
            .where(Fixture.season_id == season.id)
            .where(Fixture.status == FixtureStatus.FINISHED)
        )
        finished = result.scalar()
        result = await db.execute(
            select(func.count()).select_from(Fixture).where(Fixture.season_id == season.id)
        )
        total = result.scalar()
        print(f"   已完成: {finished} / {total}")

        # 最近 3 场
        result = await db.execute(
            select(Fixture)
            .where(Fixture.season_id == season.id)
            .where(Fixture.status == FixtureStatus.FINISHED)
            .order_by(desc(Fixture.season_day), desc(Fixture.finished_at))
            .limit(3)
        )
        for f in result.scalars().all():
            print(f"   Day {f.season_day}: {f.home_team_id[:8]}... {f.home_score}-{f.away_score} ...{f.away_team_id[:8]}")

        # 8. EventQueue 最终状态
        print("\n📍 Step 8: 演示事件最终状态")
        result = await db.execute(
            select(EventQueueModel)
            .where(EventQueueModel.payload.contains({"demo": True}))
            .order_by(EventQueueModel.id)
        )
        for e in result.scalars().all():
            icon = "✅" if e.status == EventStatus.COMPLETED.value else "⏳"
            print(f"   {icon} {e.event_type} id={e.id} → {e.status}")

        # 9. 恢复 realtime
        print("\n📍 Step 9: 恢复 realtime 模式")
        clock.set_mode("realtime")
        print(f"   ✅ 已恢复 {clock.mode} 模式")

        # 清理演示事件
        await db.execute(
            delete(EventQueueModel)
            .where(EventQueueModel.payload.contains({"demo": True}))
        )
        await db.commit()
        print("   🧹 演示事件已清理")

        print("\n" + "=" * 60)
        print("🎉 演示完成！")
        print("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

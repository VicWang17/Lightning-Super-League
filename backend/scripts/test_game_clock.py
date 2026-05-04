#!/usr/bin/env python3
"""
GameClock + EventQueue 交互式测试控制台

用法:
    cd backend && python -m scripts.test_game_clock              # 交互式模式（默认）
    cd backend && python -m scripts.test_game_clock --clock      # 显示时钟状态
    cd backend && python -m scripts.test_game_clock --events     # 显示事件队列
    cd backend && python -m scripts.test_game_clock --next       # 推进下一个事件
    cd backend && python -m scripts.test_game_clock --next 5     # 推进 5 个事件
    cd backend && python -m scripts.test_game_clock --day        # 推进 1 天
    cd backend && python -m scripts.test_game_clock --day 3      # 推进 3 天
    cd backend && python -m scripts.test_game_clock --auto 20    # 自动推进 20 个事件
    cd backend && python -m scripts.test_game_clock --mode step  # 切换时钟模式
    cd backend && python -m scripts.test_game_clock --results    # 显示最近比赛
    cd backend && python -m scripts.test_game_clock --standings  # 显示积分榜

交互式命令:
    n, next [N]   - 推进 N 个事件（默认 1）
    d, day [N]    - 推进 N 天（默认 1）
    t, tick       - 时钟 tick 1 天
    f, forward N  - 快进 N 天
    e, events     - 显示事件队列（前 20 个）
    m, mode MODE  - 切换时钟模式 (realtime/turbo/step/paused)
    c, clock      - 显示时钟状态
    r, results [N]- 显示最近 N 天比赛结果（默认 3）
    s, standings  - 显示积分榜
    i, info       - 赛季信息
    a, auto N     - 自动推进 N 个事件
    h, help       - 显示帮助
    q, quit       - 退出
"""

import asyncio
import sys
import os
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func, desc, asc

from app.config import get_settings
from app.core.clock import clock
from app.core.events import EventQueue, EventType, EventStatus
from app.services.season_service import SeasonService
from app.models.season import Season, SeasonStatus, Fixture, FixtureStatus, FixtureType
from app.models.events import EventQueue as EventQueueModel
from app.models.league import LeagueStanding

settings = get_settings()


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def print_header(title: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.END}\n")


def print_section(title: str):
    print(f"\n{Colors.BOLD}{Colors.YELLOW}▶ {title}{Colors.END}")


def print_success(msg: str):
    print(f"  {Colors.GREEN}✓ {msg}{Colors.END}")


def print_info(msg: str):
    print(f"  {Colors.BLUE}ℹ {msg}{Colors.END}")


def print_warning(msg: str):
    print(f"  {Colors.YELLOW}⚠ {msg}{Colors.END}")


def print_error(msg: str):
    print(f"  {Colors.RED}✗ {msg}{Colors.END}")


class GameClockTester:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.service = SeasonService(db)
        self.season: Optional[Season] = None

    async def refresh_season(self) -> Optional[Season]:
        result = await self.db.execute(
            select(Season)
            .where(Season.status == SeasonStatus.ONGOING)
            .order_by(desc(Season.season_number))
            .limit(1)
        )
        self.season = result.scalar_one_or_none()
        return self.season

    # ==================== 显示命令 ====================

    async def display_clock(self):
        """显示时钟状态"""
        print_section("时钟状态")
        print(f"  模式: {Colors.BOLD}{clock.mode}{Colors.END}")
        print(f"  速度: {clock.speed}x")
        print(f"  虚拟时间: {clock.now().strftime('%Y-%m-%d %H:%M:%S')}")

    async def display_events(self, limit: int = 20):
        """显示事件队列"""
        print_section(f"事件队列（前 {limit} 个）")
        result = await self.db.execute(
            select(EventQueueModel)
            .order_by(asc(EventQueueModel.scheduled_at), asc(EventQueueModel.id))
            .limit(limit)
        )
        events = result.scalars().all()
        if not events:
            print_warning("事件队列为空")
            return

        print(f"  {'ID':>4} {'类型':<20} {'状态':<12} {'计划时间':<16} {'payload'}")
        print(f"  {'-' * 70}")
        for e in events:
            scheduled = e.scheduled_at.strftime('%m-%d %H:%M') if e.scheduled_at else '-'
            payload_short = str(e.payload)[:30] + "..." if e.payload and len(str(e.payload)) > 30 else str(e.payload)
            status_color = Colors.GREEN if e.status == EventStatus.COMPLETED.value else \
                           Colors.YELLOW if e.status == EventStatus.PENDING.value else \
                           Colors.RED if e.status == EventStatus.FAILED.value else Colors.CYAN
            print(f"  {e.id:>4} {e.event_type:<20} {status_color}{e.status:<12}{Colors.END} {scheduled:<16} {payload_short}")

        # 统计
        result = await self.db.execute(
            select(EventQueueModel.status, func.count())
            .group_by(EventQueueModel.status)
        )
        counts = result.all()
        print(f"\n  统计: ", end="")
        for status, count in counts:
            print(f"{status}={count} ", end="")
        print()

    async def display_season_info(self):
        """显示赛季信息"""
        season = await self.refresh_season()
        if not season:
            print_warning("没有活跃的赛季")
            return

        print_section(f"第 {season.season_number} 赛季")
        print(f"  状态: {season.status.value}")
        print(f"  当前天数: {season.current_day} / {season.total_days}")
        print(f"  联赛轮次: {season.current_league_round}")
        print(f"  杯赛轮次: {season.current_cup_round}")
        print(f"  开始日期: {season.start_date}")
        if season.end_date:
            print(f"  结束日期: {season.end_date}")

        # 比赛统计
        result = await self.db.execute(
            select(func.count()).select_from(Fixture).where(Fixture.season_id == season.id)
        )
        total = result.scalar()
        result = await self.db.execute(
            select(func.count()).select_from(Fixture)
            .where(Fixture.season_id == season.id)
            .where(Fixture.status == FixtureStatus.FINISHED)
        )
        finished = result.scalar()
        print(f"  比赛: {finished} / {total} 已完成")

    async def display_recent_results(self, days: int = 3):
        """显示最近比赛结果"""
        season = await self.refresh_season()
        if not season:
            print_warning("没有活跃的赛季")
            return

        print_section(f"最近 {days} 天比赛结果")
        min_day = max(0, season.current_day - days)
        result = await self.db.execute(
            select(Fixture)
            .where(Fixture.season_id == season.id)
            .where(Fixture.season_day >= min_day)
            .where(Fixture.status == FixtureStatus.FINISHED)
            .order_by(desc(Fixture.season_day), desc(Fixture.finished_at))
            .limit(20)
        )
        fixtures = result.scalars().all()
        if not fixtures:
            print_warning("没有最近的比赛结果")
            return

        current_day = None
        for f in fixtures:
            if f.season_day != current_day:
                current_day = f.season_day
                print(f"\n  {Colors.BOLD}Day {current_day}{Colors.END}")
            type_icon = "🏆" if f.fixture_type == FixtureType.CUP_LIGHTNING_KNOCKOUT else \
                        "⭐" if f.fixture_type == FixtureType.CUP_LIGHTNING_GROUP else "⚽"
            print(f"    {type_icon} {f.home_team_id[:8]}... {f.home_score} - {f.away_score} ...{f.away_team_id[:8]}  ({f.fixture_type.value})")

    async def display_standings(self):
        """显示积分榜"""
        season = await self.refresh_season()
        if not season:
            print_warning("没有活跃的赛季")
            return

        print_section("积分榜 Top 10")
        result = await self.db.execute(
            select(LeagueStanding)
            .where(LeagueStanding.season_id == season.id)
            .order_by(LeagueStanding.points.desc(), LeagueStanding.goal_difference.desc())
            .limit(10)
        )
        standings = result.scalars().all()
        if not standings:
            print_warning("积分榜为空")
            return

        print(f"  {'排名':<4} {'球队':<12} {'赛':<3} {'胜':<3} {'平':<3} {'负':<3} {'进':<3} {'失':<3} {'净':<4} {'积分':<4}")
        print(f"  {'-' * 50}")
        for i, s in enumerate(standings, 1):
            print(f"  {i:<4} {s.team_id[:10]:<12} {s.played:<3} {s.won:<3} {s.drawn:<3} {s.lost:<3} "
                  f"{s.goals_for:<3} {s.goals_against:<3} {s.goal_difference:<4} {s.points:<4}")

    # ==================== 操作命令 ====================

    async def cmd_next(self, count: int = 1):
        """推进 N 个事件"""
        print_section(f"推进 {count} 个事件")
        for i in range(count):
            result = await self.service.process_next_event()
            if result is None:
                print_warning("没有更多待处理事件")
                break
            evt = result.get("event", "unknown")
            if evt == "match_day":
                print(f"  [{i+1}] ⚽ MATCH_DAY day={result.get('season_day')}, 比赛={result.get('fixtures_processed')} 场")
            elif evt == "season_end":
                print(f"  [{i+1}] 🏁 SEASON_END")
                break
            elif evt == "cup_progression":
                print(f"  [{i+1}] 🏆 CUP_PROGRESSION")
            elif evt == "promotion_relegation":
                print(f"  [{i+1}] ⬆️⬇️ PROMOTION_RELEGATION")
            else:
                print(f"  [{i+1}] 📋 {evt}")

    async def cmd_day(self, count: int = 1):
        """推进 N 天（兼容旧接口，处理到 MATCH_DAY 为止）"""
        season = await self.refresh_season()
        if not season:
            print_warning("没有活跃的赛季")
            return

        print_section(f"推进 {count} 天")
        for i in range(count):
            result = await self.service.process_next_day(season)
            day = result.get("season_day", "?")
            fixtures = result.get("fixtures_processed", 0)
            if fixtures > 0:
                print(f"  Day {day}: {fixtures} 场比赛已处理")
            else:
                print(f"  Day {day}: 无比赛")
            await self.db.refresh(season)
            if season.status == SeasonStatus.FINISHED:
                print_success("赛季已结束！")
                break

    async def cmd_tick(self):
        """时钟 tick 1 天"""
        clock.tick(timedelta(days=1))
        print_success(f"时钟已推进 1 天，现在: {clock.now().strftime('%Y-%m-%d')}")

    async def cmd_forward(self, days: int):
        """快进 N 天"""
        season = await self.refresh_season()
        if not season:
            print_warning("没有活跃的赛季")
            return

        target = season.current_day + days
        print_section(f"快进到第 {target} 天")
        results = await self.service.fast_forward(target, season)
        await self.db.refresh(season)
        print_success(f"处理了 {len(results)} 个事件，现在第 {season.current_day} 天")

    async def cmd_auto(self, count: int):
        """自动推进 N 个事件"""
        print_section(f"自动推进 {count} 个事件")
        processed = 0
        while processed < count:
            result = await self.service.process_next_event()
            if result is None:
                print_warning("没有更多事件，停止")
                break
            processed += 1
            if result.get("event") == "match_day":
                print(f"  [{processed}] Day {result.get('season_day')}: {result.get('fixtures_processed')} 场")
            elif result.get("event") == "season_end":
                print(f"  [{processed}] 🏁 赛季结束")
                break
        print_success(f"共处理 {processed} 个事件")

    async def cmd_mode(self, mode: str):
        """切换时钟模式"""
        if mode not in ("realtime", "turbo", "step", "paused"):
            print_error(f"无效模式: {mode}，可选: realtime, turbo, step, paused")
            return
        clock.set_mode(mode)
        print_success(f"时钟已切换为 {mode} 模式")

    # ==================== 交互式模式 ====================

    async def interactive_mode(self):
        print_header("⚡ GameClock + EventQueue 交互式控制台")
        print(f"""
  {Colors.CYAN}命令:{Colors.END}
    n, next [N]    - 推进 N 个事件（默认 1）
    d, day [N]     - 推进 N 天（默认 1）
    t, tick        - 时钟 tick 1 天
    f, forward N   - 快进 N 天
    e, events      - 显示事件队列
    m, mode MODE   - 切换时钟模式
    c, clock       - 显示时钟状态
    r, results [N] - 显示最近 N 天结果
    s, standings   - 显示积分榜
    i, info        - 赛季信息
    a, auto N      - 自动推进 N 个事件
    h, help        - 显示帮助
    q, quit        - 退出
        """)

        await self.display_clock()
        await self.display_season_info()

        while True:
            try:
                season = await self.refresh_season()
                prefix = f"[S{season.season_number if season else '?'}D{season.current_day if season else '?'}]"
                cmd = input(f"\n{Colors.BOLD}{Colors.CYAN}{prefix}{Colors.END} > ").strip().lower()

                if not cmd:
                    continue

                parts = cmd.split()
                action = parts[0]

                if action in ('n', 'next'):
                    count = int(parts[1]) if len(parts) > 1 else 1
                    await self.cmd_next(count)

                elif action in ('d', 'day'):
                    count = int(parts[1]) if len(parts) > 1 else 1
                    await self.cmd_day(count)

                elif action in ('t', 'tick'):
                    await self.cmd_tick()

                elif action in ('f', 'forward'):
                    days = int(parts[1]) if len(parts) > 1 else 5
                    await self.cmd_forward(days)

                elif action in ('e', 'events'):
                    limit = int(parts[1]) if len(parts) > 1 else 20
                    await self.display_events(limit)

                elif action in ('m', 'mode'):
                    mode = parts[1] if len(parts) > 1 else "step"
                    await self.cmd_mode(mode)

                elif action in ('c', 'clock'):
                    await self.display_clock()

                elif action in ('r', 'results'):
                    days = int(parts[1]) if len(parts) > 1 else 3
                    await self.display_recent_results(days)

                elif action in ('s', 'standings'):
                    await self.display_standings()

                elif action in ('i', 'info'):
                    await self.display_season_info()

                elif action in ('a', 'auto'):
                    count = int(parts[1]) if len(parts) > 1 else 10
                    await self.cmd_auto(count)

                elif action in ('h', 'help'):
                    print(f"""
  {Colors.CYAN}命令:{Colors.END}
    n, next [N]    - 推进 N 个事件
    d, day [N]     - 推进 N 天
    t, tick        - 时钟 tick 1 天
    f, forward N   - 快进 N 天
    e, events [N]  - 显示事件队列
    m, mode MODE   - 切换时钟模式 (realtime/turbo/step/paused)
    c, clock       - 显示时钟状态
    r, results [N] - 显示最近 N 天结果
    s, standings   - 显示积分榜
    i, info        - 赛季信息
    a, auto N      - 自动推进 N 个事件
    h, help        - 显示帮助
    q, quit        - 退出
                    """)

                elif action in ('q', 'quit', 'exit'):
                    print("\n  再见！")
                    break

                else:
                    print_error(f"未知命令: {action}，输入 h 查看帮助")

            except KeyboardInterrupt:
                print("\n\n  再见！")
                break
            except Exception as e:
                print_error(str(e))
                import traceback
                traceback.print_exc()


async def main():
    parser = argparse.ArgumentParser(description="GameClock + EventQueue 测试控制台")
    parser.add_argument("--clock", action="store_true", help="显示时钟状态")
    parser.add_argument("--events", action="store_true", help="显示事件队列")
    parser.add_argument("--next", type=int, nargs="?", const=1, metavar="N", help="推进 N 个事件")
    parser.add_argument("--day", type=int, nargs="?", const=1, metavar="N", help="推进 N 天")
    parser.add_argument("--auto", type=int, metavar="N", help="自动推进 N 个事件")
    parser.add_argument("--forward", type=int, metavar="N", help="快进 N 天")
    parser.add_argument("--mode", type=str, metavar="MODE", help="切换时钟模式")
    parser.add_argument("--results", type=int, nargs="?", const=3, metavar="N", help="显示最近 N 天结果")
    parser.add_argument("--standings", action="store_true", help="显示积分榜")
    parser.add_argument("--info", action="store_true", help="显示赛季信息")
    args = parser.parse_args()

    engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        tester = GameClockTester(db)

        # 如果没有任何参数，进入交互模式
        if not any([args.clock, args.events, args.next, args.day, args.auto,
                    args.forward, args.mode, args.results, args.standings, args.info]):
            await tester.interactive_mode()
            return

        # 命令行模式
        if args.clock:
            await tester.display_clock()
        if args.mode:
            await tester.cmd_mode(args.mode)
        if args.events:
            await tester.display_events()
        if args.next:
            await tester.cmd_next(args.next)
        if args.day:
            await tester.cmd_day(args.day)
        if args.forward:
            await tester.cmd_forward(args.forward)
        if args.auto:
            await tester.cmd_auto(args.auto)
        if args.results:
            await tester.display_recent_results(args.results)
        if args.standings:
            await tester.display_standings()
        if args.info:
            await tester.display_season_info()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

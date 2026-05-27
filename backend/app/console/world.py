from __future__ import annotations

import time

from app.console import panels, ui
from app.services.simulation_runner import RunnerResult


def ask_watch_settings() -> tuple[float, float]:
    ui.header("观察世界时间流逝")
    print("选择世界时间倍速：")
    print("  1   20x    真实 1 秒 = 游戏 20 秒（常规观察）")
    print("  2   100x   真实 1 秒 = 游戏 100 秒")
    print("  3   300x   真实 1 秒 = 游戏 5 分钟")
    print("  4   1800x  真实 1 秒 = 游戏 30 分钟（推荐快测）")
    print("  5   3600x  真实 1 秒 = 游戏 1 小时")
    print("  6   自定义")
    choice = input("倍速 > ").strip() or "4"
    if choice == "1":
        speed = 20.0
    elif choice == "2":
        speed = 100.0
    elif choice == "3":
        speed = 300.0
    elif choice == "5":
        speed = 3600.0
    elif choice == "6":
        speed = ui.ask_float("输入倍速，例如 1800 表示 1 秒 = 游戏 30 分钟", 1800.0)
    else:
        speed = 1800.0

    print()
    print("刷新频率：")
    print("  1   稳定：每 1.0 秒刷新")
    print("  2   平滑：每 0.5 秒刷新（推荐）")
    print("  3   高频：每 0.25 秒刷新")
    refresh = input("刷新频率 > ").strip() or "2"
    interval = 1.0 if refresh == "1" else 0.25 if refresh == "3" else 0.5
    return speed, interval


async def watch(runner, speed: float, interval_seconds: float, monitor_mode: bool = False) -> None:
    if runner.shared_clock:
        await runner.shared_clock.set_mode("turbo", speed=speed)
        await runner.db.commit()
    else:
        runner.clock.set_mode("turbo", speed=speed)

    iteration = 0
    while True:
        iteration += 1
        result = await runner.process_due_events(max_events=200)
        status = await runner.status()

        if monitor_mode:
            standings = await runner.get_standings_snapshot()
            scores = await runner.get_daily_scores()
            top_players = await runner.get_top_players(limit=5)
            records = await runner.get_records_snapshot(limit=5)
            health = await runner.get_data_health_report()
            panels.render_monitor(
                status, result, speed, interval_seconds, iteration,
                standings=standings,
                daily_scores=scores,
                top_players=top_players,
                records=records,
                health=health,
            )
        else:
            panels.render_world(status, result, speed, interval_seconds, iteration)

        time.sleep(max(0.0, interval_seconds))


async def advance_next(runner) -> None:
    result = await runner.run_next_event_time(max_events_at_time=200)
    status = await runner.status()
    panels.print_runner_result(result, now=(status.get("clock") or {}).get("virtual_now"))


async def run_days(runner) -> None:
    days = ui.ask_int("虚拟天数", 1)
    result = await runner.run_for_virtual_days(days=days, step_hours=24)
    status = await runner.status()
    panels.print_runner_result(result, now=(status.get("clock") or {}).get("virtual_now"))


async def run_seasons(runner) -> None:
    count = ui.ask_int("赛季数量", 1)
    max_events = ui.ask_int("最大事件数", 10000 * count)
    result = await runner.run_seasons(count=count, max_events=max_events)
    status = await runner.status()
    panels.print_runner_result(result, now=(status.get("clock") or {}).get("virtual_now"))
    errors = await runner.assert_basic_invariants()
    if errors:
        ui.error("invariant errors: " + "; ".join(errors))


async def watch_cli(
    runner,
    mode: str,
    speed: float,
    interval_seconds: float,
    step_hours: int,
    max_iterations: int,
    max_events_at_time: int,
    monitor_mode: bool = False,
) -> None:
    if runner.shared_clock:
        await runner.shared_clock.set_mode("turbo", speed=speed)
        await runner.db.commit()
    else:
        runner.clock.set_mode("turbo", speed=speed)

    iteration = 0
    while max_iterations <= 0 or iteration < max_iterations:
        iteration += 1
        if mode == "next-event":
            result = await runner.run_next_event_time(max_events_at_time=max_events_at_time)
        elif mode == "tick":
            result = await runner.run_for_virtual_days(days=1, step_hours=step_hours)
        else:
            result = await runner.process_due_events(max_events=max_events_at_time)

        status = await runner.status()

        if monitor_mode:
            standings = await runner.get_standings_snapshot()
            scores = await runner.get_daily_scores()
            top_players = await runner.get_top_players(limit=5)
            records = await runner.get_records_snapshot(limit=5)
            health = await runner.get_data_health_report()
            panels.render_monitor(
                status, result, speed, interval_seconds, iteration,
                standings=standings,
                daily_scores=scores,
                top_players=top_players,
                records=records,
                health=health,
            )
        else:
            panels.render_world(status, result, speed, interval_seconds, iteration)

        if result.stopped_reason in {"no_pending_events", "max_events", "max_events_at_same_time"}:
            return
        time.sleep(max(0.0, interval_seconds))

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy.exc import SQLAlchemyError

from app.console import actions, api_mode, panels, ui, world
from app.console.context import with_runner


async def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "watch":
            if args.runtime == "api":
                api_mode.watch_api(
                    api_mode.ApiModeContext(),
                    speed=args.speed,
                    interval_seconds=args.interval,
                    monitor_mode=args.monitor,
                )
            else:
                await with_runner(
                    lambda runner: world.watch_cli(
                        runner,
                        mode=args.mode,
                        speed=args.speed,
                        interval_seconds=args.interval,
                        step_hours=args.step_hours,
                        max_iterations=args.max_iterations,
                        max_events_at_time=args.max_events_at_time,
                        monitor_mode=args.monitor,
                    )
                )
        elif args.command == "bootstrap":
            actions.bootstrap(yes=args.yes)
        elif args.command == "status":
            await with_runner(show_status)
        elif args.command == "check":
            await with_runner(show_checks)
        elif args.command == "engine":
            await actions.engine_health()
        else:
            await main_menu()
    except SQLAlchemyError as exc:
        ui.error(f"database operation failed: {exc}")
        ui.warning("如果本地库未准备好，先在 console 里执行 数据初始化 -> 一键重建开发数据")
        raise SystemExit(1) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lightning Super League test console")
    sub = parser.add_subparsers(dest="command")

    watch_parser = sub.add_parser("watch", help="Run world observer directly")
    watch_parser.add_argument("--mode", choices=["continuous", "next-event", "tick"], default="continuous")
    watch_parser.add_argument("--runtime", choices=["core", "api"], default="core")
    watch_parser.add_argument("--speed", type=float, default=20.0)
    watch_parser.add_argument("--interval", type=float, default=0.5)
    watch_parser.add_argument("--step-hours", type=int, default=1)
    watch_parser.add_argument("--max-iterations", type=int, default=0)
    watch_parser.add_argument("--max-events-at-time", type=int, default=200)
    watch_parser.add_argument("--monitor", action="store_true", help="启用 AI 综合监控模式，输出积分榜/比分/球员榜/纪录/健康检查")

    bootstrap_parser = sub.add_parser("bootstrap", help="Reset dev data and create first season")
    bootstrap_parser.add_argument("--yes", action="store_true")

    sub.add_parser("status", help="Show status")
    sub.add_parser("check", help="Run basic invariant checks")
    sub.add_parser("engine", help="Check match engine")
    return parser


async def main_menu() -> None:
    while True:
        choice = ui.menu(
            "Lightning Super League Test Console",
            [
                ui.MenuItem("1", "世界运行", "观察、暂停、倍速、快进", highlight=True),
                ui.MenuItem("2", "数据初始化", "基础设施、迁移、首赛季"),
                ui.MenuItem("3", "状态检查", "总览、invariant、诊断"),
                ui.MenuItem("4", "比赛与引擎", "健康检查、结果、当前耦合状态"),
                ui.MenuItem("5", "长流程压测", "跑 1/10/100 个赛季"),
                ui.MenuItem("6", "设置", "时钟模式、倍速"),
                ui.MenuItem("0", "退出"),
            ],
        )
        try:
            if choice in {"0", "q", "quit"}:
                return
            if choice == "1":
                await world_menu()
            elif choice == "2":
                await init_menu()
            elif choice == "3":
                await status_menu()
            elif choice == "4":
                await match_menu()
            elif choice == "5":
                await stress_menu()
            elif choice == "6":
                await settings_menu()
            else:
                ui.warning("未知选项")
                ui.pause()
        except KeyboardInterrupt:
            ui.warning("操作已中断")
            ui.pause()
        except Exception as exc:
            ui.error(f"operation failed: {exc}")
            ui.pause()


async def world_menu() -> None:
    while True:
        choice = ui.menu(
            "世界运行",
            [
                ui.MenuItem("1", "启动观察模式（Core）", "直接调用 service，适合压测", highlight=True),
                ui.MenuItem("2", "启动观察模式（API）", "检查/启动前后端，通过 HTTP 推进"),
                ui.MenuItem("3", "启动 AI 监看模式（Core）", "综合监控：积分榜/比分/球员榜/纪录/健康", highlight=True),
                ui.MenuItem("4", "启动 AI 监看模式（API）", "综合监控（API 模式）", highlight=True),
                ui.MenuItem("5", "暂停世界时间"),
                ui.MenuItem("6", "恢复 20x 世界时间"),
                ui.MenuItem("7", "设置倍速"),
                ui.MenuItem("8", "推进到下一个事件"),
                ui.MenuItem("9", "快进 N 天"),
                ui.MenuItem("0", "返回"),
            ],
        )
        if choice == "0":
            return
        if choice == "1":
            speed, interval = world.ask_watch_settings()
            await with_runner(lambda runner: world.watch(runner, speed, interval, monitor_mode=False))
        elif choice == "2":
            speed, interval = world.ask_watch_settings()
            api_mode.watch_api(api_mode.ApiModeContext(), speed=speed, interval_seconds=interval, monitor_mode=False)
        elif choice == "3":
            speed, interval = world.ask_watch_settings()
            await with_runner(lambda runner: world.watch(runner, speed, interval, monitor_mode=True))
        elif choice == "4":
            speed, interval = world.ask_watch_settings()
            api_mode.watch_api(api_mode.ApiModeContext(), speed=speed, interval_seconds=interval, monitor_mode=True)
        elif choice == "5":
            await with_runner(lambda runner: actions.set_clock(runner, "paused", None))
            ui.pause()
        elif choice == "6":
            await with_runner(lambda runner: actions.set_clock(runner, "turbo", 20.0))
            ui.pause()
        elif choice == "7":
            speed = ui.ask_float("倍速", 20.0)
            await with_runner(lambda runner: actions.set_clock(runner, "turbo", speed))
            ui.pause()
        elif choice == "8":
            await with_runner(world.advance_next)
            ui.pause()
        elif choice == "9":
            await with_runner(world.run_days)
            ui.pause()


async def init_menu() -> None:
    while True:
        choice = ui.menu(
            "数据初始化",
            [
                ui.MenuItem("1", "一键重建开发数据 + 创建首赛季", "会删除开发数据", highlight=True),
                ui.MenuItem("2", "启动基础设施"),
                ui.MenuItem("3", "运行迁移"),
                ui.MenuItem("4", "仅创建新赛季"),
                ui.MenuItem("0", "返回"),
            ],
        )
        if choice == "0":
            return
        if choice == "1":
            actions.bootstrap(yes=False)
        elif choice == "2":
            actions.run(["make", "infra-up"], actions.REPO_ROOT, actions.os.environ.copy())
        elif choice == "3":
            env = actions.base_env()
            actions.run([actions.PYTHON, "-m", "alembic", "upgrade", "head"], actions.BACKEND_DIR, env)
        elif choice == "4":
            env = actions.base_env()
            actions.run([actions.PYTHON, "-m", "scripts.init_season"], actions.BACKEND_DIR, env)
        ui.pause()


async def status_menu() -> None:
    while True:
        choice = ui.menu(
            "状态检查",
            [
                ui.MenuItem("1", "总览"),
                ui.MenuItem("2", "基础 invariant 检查"),
                ui.MenuItem("3", "最近比赛结果"),
                ui.MenuItem("4", "数据健康报告"),
                ui.MenuItem("5", "积分榜"),
                ui.MenuItem("6", "每日比分"),
                ui.MenuItem("7", "球员排行榜"),
                ui.MenuItem("8", "最新纪录"),
                ui.MenuItem("0", "返回"),
            ],
        )
        if choice == "0":
            return
        if choice == "1":
            await with_runner(show_status)
        elif choice == "2":
            await with_runner(show_checks)
        elif choice == "3":
            await with_runner(show_results)
        elif choice == "4":
            await with_runner(show_health)
        elif choice == "5":
            await with_runner(show_standings)
        elif choice == "6":
            await with_runner(show_daily_scores)
        elif choice == "7":
            await with_runner(show_top_players)
        elif choice == "8":
            await with_runner(show_records)
        ui.pause()


async def match_menu() -> None:
    while True:
        choice = ui.menu(
            "比赛与引擎",
            [
                ui.MenuItem("1", "引擎健康检查"),
                ui.MenuItem("2", "最近比赛结果"),
                ui.MenuItem("3", "当前耦合状态说明"),
                ui.MenuItem("0", "返回"),
            ],
        )
        if choice == "0":
            return
        if choice == "1":
            await actions.engine_health()
        elif choice == "2":
            await with_runner(show_results)
        elif choice == "3":
            ui.section("当前比赛引擎状态")
            print("当前模式: sync-final-result")
            print("Go 引擎是真实计算结果，但同步返回最终结果。")
            print("尚未实现 match session、tick 推送、战术 command API。")
        ui.pause()


async def stress_menu() -> None:
    while True:
        choice = ui.menu(
            "长流程压测",
            [
                ui.MenuItem("1", "跑 1 个赛季"),
                ui.MenuItem("2", "跑 10 个赛季"),
                ui.MenuItem("3", "跑 100 个赛季"),
                ui.MenuItem("4", "自定义"),
                ui.MenuItem("0", "返回"),
            ],
        )
        if choice == "0":
            return
        count = {"1": 1, "2": 10, "3": 100}.get(choice)
        if choice == "4":
            count = ui.ask_int("赛季数量", 1)
        if count:
            await with_runner(lambda runner: run_stress(runner, count))
            ui.pause()


async def settings_menu() -> None:
    while True:
        choice = ui.menu(
            "设置",
            [
                ui.MenuItem("1", "设置世界倍速"),
                ui.MenuItem("2", "暂停世界时间"),
                ui.MenuItem("3", "恢复 realtime"),
                ui.MenuItem("0", "返回"),
            ],
        )
        if choice == "0":
            return
        if choice == "1":
            speed = ui.ask_float("倍速", 20.0)
            await with_runner(lambda runner: actions.set_clock(runner, "turbo", speed))
        elif choice == "2":
            await with_runner(lambda runner: actions.set_clock(runner, "paused", None))
        elif choice == "3":
            await with_runner(lambda runner: actions.set_clock(runner, "realtime", None))
        ui.pause()


async def show_status(runner) -> None:
    panels.print_status(await runner.status())


async def show_checks(runner) -> None:
    errors = await runner.assert_basic_invariants()
    if errors:
        ui.error("invariant errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        ui.success("basic invariants passed")


async def show_results(runner) -> None:
    rows = await runner.recent_results(limit=10)
    if not rows:
        ui.warning("no match results")
        return
    for row in rows:
        print(
            f"day={row['day']:>2} {row['home_team_id'][:8]} "
            f"{row['home_score']} - {row['away_score']} {row['away_team_id'][:8]} "
            f"{row['type']} [{row['resolution']}]"
        )


async def show_health(runner) -> None:
    health = await runner.get_data_health_report()
    panels.render_data_health(health)


async def show_standings(runner) -> None:
    standings = await runner.get_standings_snapshot()
    if not standings:
        ui.warning("no standings available")
        return
    panels.render_standings(standings)


async def show_daily_scores(runner) -> None:
    status = await runner.status()
    season = status.get("season") or {}
    day = season.get("day")
    scores = await runner.get_daily_scores(day=day)
    if not scores:
        ui.warning("no scores for current day")
        return
    panels.render_daily_scores(scores, day=day)


async def show_top_players(runner) -> None:
    top = await runner.get_top_players(limit=10)
    panels.render_top_players(top)


async def show_records(runner) -> None:
    records = await runner.get_records_snapshot(limit=20)
    if not records:
        ui.warning("no records available")
        return
    panels.render_records(records)


async def run_stress(runner, count: int) -> None:
    max_events = 10000 * count
    result = await runner.run_seasons(count=count, max_events=max_events)
    status = await runner.status()
    panels.print_runner_result(result, now=(status.get("clock") or {}).get("virtual_now"))
    errors = await runner.assert_basic_invariants()
    if errors:
        ui.error("invariant errors: " + "; ".join(errors))


if __name__ == "__main__":
    asyncio.run(main())

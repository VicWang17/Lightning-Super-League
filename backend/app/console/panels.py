from __future__ import annotations

from app.console import ui
from app.services.simulation_runner import RunnerResult


def result_line(item: dict) -> str:
    event = item.get("event", "unknown")
    if event == "match_day":
        return f"MATCH_DAY day={item.get('season_day')} fixtures={item.get('fixtures_processed')}"
    if event == "season_end":
        return f"SEASON_END #{item.get('season_number')} -> #{item.get('next_season_number')}"
    if event == "cup_progression":
        return f"CUP_PROGRESSION after_day={item.get('after_day')}"
    if event == "promotion_relegation":
        return f"PROMOTION_RELEGATION day={item.get('day')}"
    return event


def print_status(status: dict) -> None:
    clock = status.get("clock") or {}
    season = status.get("season") or {}

    ui.section("时钟")
    print(f"mode={clock.get('mode')} speed={clock.get('speed')} virtual_now={clock.get('virtual_now')}")

    ui.section("赛季")
    if season:
        print(f"#{season.get('number')} day={season.get('day')}/{season.get('total_days')} status={season.get('status')}")
    else:
        print("none")

    ui.section("事件")
    print(ui.format_counts(status.get("events") or {}))
    next_event = status.get("next_event")
    if next_event:
        print(f"next=#{next_event['id']} {next_event['type']} at {next_event['scheduled_at']} payload={next_event['payload']}")
    else:
        print("next=none")

    ui.section("比赛")
    print(ui.format_counts(status.get("fixtures") or {}))
    print(f"match_results={status.get('match_results', 0)} failed_events={status.get('failed_events', 0)}")


def print_runner_result(result: RunnerResult, now: str | None = None) -> None:
    suffix = f" now={now}" if now else ""
    print(
        f"processed={result.processed} season_ends={result.season_ends} "
        f"stopped_reason={result.stopped_reason}{suffix}"
    )
    for item in result.results[-8:]:
        print(f"  {result_line(item)}")
    if len(result.results) > 8:
        print(f"  ... {len(result.results) - 8} earlier results")


def render_world(status: dict, result: RunnerResult, speed: float, interval: float, iteration: int) -> None:
    ui.clear_screen()
    clock = status.get("clock") or {}
    season = status.get("season") or {}
    fixtures = status.get("fixtures") or {}
    events = status.get("events") or {}
    next_event = status.get("next_event")

    day = season.get("day", 0) if season else 0
    total_days = season.get("total_days", 0) if season else 0
    progress = day / total_days if total_days else 0

    print(f"{ui.C.BOLD}{ui.C.CYAN}Lightning Super League 世界观察器{ui.C.END}")
    print("=" * 78)
    print(f"速度: {ui.C.GREEN}{speed:g}x{ui.C.END}    刷新: {interval:g}s    模式: {clock.get('mode', '-')}")
    print(f"虚拟时间: {ui.C.BOLD}{clock.get('virtual_now', '-')}{ui.C.END}")
    print("-" * 78)

    if season:
        print(f"赛季: 第 {season.get('number')} 赛季    天数: {day}/{total_days}    状态: {season.get('status')}")
        print(f"进度: {ui.progress_bar(progress, 36)} {progress * 100:5.1f}%")
    else:
        print("赛季: 无活跃赛季")
        print(f"进度: {ui.progress_bar(0, 36)}   0.0%")

    print("-" * 78)
    print(f"事件队列: {ui.format_counts(events)}")
    if next_event:
        print(f"下一事件: #{next_event['id']} {next_event['type']} at {next_event['scheduled_at']}")
    else:
        print("下一事件: 无")
    print(f"比赛: {ui.format_counts(fixtures)}    结果数: {status.get('match_results', 0)}")
    print(f"失败事件: {status.get('failed_events', 0)}")
    print("-" * 78)
    print(
        f"本轮处理: events={result.processed} season_ends={result.season_ends} "
        f"reason={result.stopped_reason} tick={iteration}"
    )
    if result.results:
        print("最近处理:")
        for item in result.results[-5:]:
            print(f"  {result_line(item)}")
    else:
        print("最近处理: 无到期事件")
    print("-" * 78)
    print("Ctrl+C 停止观察并返回菜单")

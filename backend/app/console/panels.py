from __future__ import annotations

from typing import Any

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


# =============================================================================
# 增强监控面板（供 AI 监看模式使用）
# =============================================================================

def render_monitor(
    status: dict,
    result: RunnerResult,
    speed: float,
    interval: float,
    iteration: int,
    standings: dict[str, list[dict]] | None = None,
    daily_scores: list[dict] | None = None,
    top_players: dict[str, list[dict]] | None = None,
    records: list[dict] | None = None,
    health: dict[str, Any] | None = None,
) -> None:
    """综合监控面板：输出赛季进度 + 积分榜 + 每日比分 + 球员榜 + 纪录 + 健康检查"""
    ui.clear_screen()
    clock = status.get("clock") or {}
    season = status.get("season") or {}
    fixtures = status.get("fixtures") or {}
    events = status.get("events") or {}
    next_event = status.get("next_event")

    day = season.get("day", 0) if season else 0
    total_days = season.get("total_days", 0) if season else 0
    progress = day / total_days if total_days else 0

    # ---- Header ----
    print(f"{ui.C.BOLD}{ui.C.CYAN}Lightning Super League 综合监控面板{ui.C.END}")
    print("=" * 78)
    print(f"速度: {ui.C.GREEN}{speed:g}x{ui.C.END}  刷新: {interval:g}s  模式: {clock.get('mode', '-')}  tick={iteration}")
    print(f"虚拟时间: {ui.C.BOLD}{clock.get('virtual_now', '-')}{ui.C.END}")
    print("-" * 78)

    if season:
        print(f"赛季: 第 {season.get('number')} 赛季  天数: {day}/{total_days}  状态: {season.get('status')}")
        print(f"进度: {ui.progress_bar(progress, 36)} {progress * 100:5.1f}%")
    else:
        print("赛季: 无活跃赛季")
    print(f"事件: {ui.format_counts(events)}  |  比赛: {ui.format_counts(fixtures)}  |  结果: {status.get('match_results', 0)}")
    print(f"失败事件: {status.get('failed_events', 0)}  |  本轮处理: {result.processed}  reason={result.stopped_reason}")
    print("-" * 78)

    # ---- 健康检查 ----
    if health:
        _render_health_compact(health)
        print("-" * 78)

    # ---- 每日比分 ----
    if daily_scores:
        _render_daily_scores_compact(daily_scores)
        print("-" * 78)

    # ---- 积分榜 ----
    if standings:
        _render_standings_compact(standings)
        print("-" * 78)

    # ---- 球员榜 ----
    if top_players:
        _render_top_players_compact(top_players)
        print("-" * 78)

    # ---- 纪录 ----
    if records:
        _render_records_compact(records)
        print("-" * 78)

    print("Ctrl+C 停止观察")


def _render_health_compact(health: dict[str, Any]) -> None:
    ok = health.get("ok", False)
    icon = f"{ui.C.GREEN}✓{ui.C.END}" if ok else f"{ui.C.RED}✗{ui.C.END}"
    print(f"{ui.C.BOLD}数据健康:{ui.C.END} {icon}  season_day={health.get('season_day')}  season=#{health.get('season_number')}")
    for err in health.get("errors", []):
        print(f"  {ui.C.RED}ERR {err}{ui.C.END}")
    for warn in health.get("warnings", []):
        print(f"  {ui.C.YELLOW}WARN {warn}{ui.C.END}")


def _render_daily_scores_compact(scores: list[dict]) -> None:
    print(f"{ui.C.BOLD}每日比分 ({len(scores)} 场){ui.C.END}")
    for s in scores[:8]:
        home = s.get("home_team_id", "")[:8]
        away = s.get("away_team_id", "")[:8]
        typ = s.get("fixture_type", "")[:4]
        res = s.get("resolution", "")[:3]
        print(f"  [{typ}] {home} {s.get('home_score', '-')}:{s.get('away_score', '-')} {away} ({res})")
    if len(scores) > 8:
        print(f"  ... 还有 {len(scores) - 8} 场")


def _render_standings_compact(standings: dict[str, list[dict]]) -> None:
    print(f"{ui.C.BOLD}积分榜 (顶级联赛){ui.C.END}")
    for league_name, rows in standings.items():
        print(f"  {ui.C.CYAN}{league_name}{ui.C.END}")
        for r in rows[:6]:
            name = r.get("team_name", "")[:10]
            print(
                f"    {r.get('position', 0):>2}. {name:<10} "
                f"{r.get('played', 0)}场 {r.get('won', 0)}-{r.get('drawn', 0)}-{r.get('lost', 0)} "
                f"{r.get('goals_for', 0)}:{r.get('goals_against', 0)} "
                f"{ui.C.BOLD}{r.get('points', 0)}分{ui.C.END}"
            )
        if len(rows) > 6:
            print(f"    ... 共 {len(rows)} 队")


def _render_top_players_compact(top_players: dict[str, list[dict]]) -> None:
    goals = top_players.get("goals", [])
    assists = top_players.get("assists", [])
    ratings = top_players.get("rating", [])

    print(f"{ui.C.BOLD}球员榜{ui.C.END}")
    if goals:
        line = "射手: " + ", ".join(f"{g['name'][:8]}({g['goals']})" for g in goals[:5])
        print(f"  {line}")
    if assists:
        line = "助攻: " + ", ".join(f"{a['name'][:8]}({a['assists']})" for a in assists[:5])
        print(f"  {line}")
    if ratings:
        line = "评分: " + ", ".join(f"{r['name'][:8]}({r['rating']})" for r in ratings[:5])
        print(f"  {line}")


def _render_records_compact(records: list[dict]) -> None:
    print(f"{ui.C.BOLD}最新纪录{ui.C.END}")
    for r in records[:5]:
        print(f"  {r.get('record_type', '')}: {r.get('holder_name', '?')} {r.get('record_value', '')}")


def render_standings(standings: dict[str, list[dict]]) -> None:
    """独立渲染积分榜（菜单模式用）"""
    ui.clear_screen()
    print(f"{ui.C.BOLD}{ui.C.CYAN}积分榜{ui.C.END}")
    print("=" * 78)
    for league_name, rows in standings.items():
        print(f"\n{ui.C.CYAN}{league_name}{ui.C.END}")
        print(f"{'排名':<4} {'球队':<14} {'赛':<3} {'胜':<3} {'平':<3} {'负':<3} {'进':<3} {'失':<3} {'净':<4} {'积分':<4}")
        print("-" * 50)
        for r in rows:
            print(
                f"{r.get('position', 0):<4} {r.get('team_name', '')[:14]:<14} "
                f"{r.get('played', 0):<3} {r.get('won', 0):<3} {r.get('drawn', 0):<3} {r.get('lost', 0):<3} "
                f"{r.get('goals_for', 0):<3} {r.get('goals_against', 0):<3} {r.get('goal_difference', 0):<4} "
                f"{ui.C.BOLD}{r.get('points', 0)}{ui.C.END}"
            )
    print("-" * 78)


def render_daily_scores(scores: list[dict], day: int | None = None) -> None:
    """独立渲染每日比分（菜单模式用）"""
    ui.clear_screen()
    title = f"每日比分 (Day {day})" if day is not None else "每日比分"
    print(f"{ui.C.BOLD}{ui.C.CYAN}{title}{ui.C.END}")
    print("=" * 78)
    if not scores:
        print("无比赛结果")
        return
    for s in scores:
        home = s.get("home_team_id", "")[:12]
        away = s.get("away_team_id", "")[:12]
        typ = s.get("fixture_type", "")
        res = s.get("resolution", "")
        print(f"[{typ:>6}] {home:>12} {s.get('home_score', '-')}:{s.get('away_score', '-')} {away:<12} ({res})")
    print("-" * 78)


def render_top_players(top_players: dict[str, list[dict]]) -> None:
    """独立渲染球员榜（菜单模式用）"""
    ui.clear_screen()
    print(f"{ui.C.BOLD}{ui.C.CYAN}球员排行榜{ui.C.END}")
    print("=" * 78)

    goals = top_players.get("goals", [])
    assists = top_players.get("assists", [])
    ratings = top_players.get("rating", [])

    if goals:
        print(f"\n{ui.C.CYAN}射手榜{ui.C.END}")
        for i, g in enumerate(goals, 1):
            print(f"  {i}. {g.get('name', '?')}  {g.get('goals', 0)}球")

    if assists:
        print(f"\n{ui.C.CYAN}助攻榜{ui.C.END}")
        for i, a in enumerate(assists, 1):
            print(f"  {i}. {a.get('name', '?')}  {a.get('assists', 0)}次")

    if ratings:
        print(f"\n{ui.C.CYAN}评分榜{ui.C.END}")
        for i, r in enumerate(ratings, 1):
            print(f"  {i}. {r.get('name', '?')}  {r.get('rating', 0)}分 ({r.get('matches', 0)}场)")

    print("-" * 78)


def render_records(records: list[dict]) -> None:
    """独立渲染纪录（菜单模式用）"""
    ui.clear_screen()
    print(f"{ui.C.BOLD}{ui.C.CYAN}最新纪录{ui.C.END}")
    print("=" * 78)
    if not records:
        print("无纪录")
        return
    for r in records:
        cat = r.get("category", "")
        print(f"[{cat}] {r.get('record_type', '')}: {r.get('holder_name', '?')} {r.get('record_value', '')}")
    print("-" * 78)


def render_data_health(health: dict[str, Any]) -> None:
    """独立渲染健康报告（菜单模式用）"""
    ui.clear_screen()
    print(f"{ui.C.BOLD}{ui.C.CYAN}数据健康报告{ui.C.END}")
    print("=" * 78)
    ok = health.get("ok", False)
    if ok:
        ui.success("所有检查通过")
    else:
        ui.error("存在数据异常")
    print(f"赛季: 第 {health.get('season_number')} 赛季  Day {health.get('season_day')}")
    if health.get("errors"):
        print(f"\n{ui.C.RED}错误:{ui.C.END}")
        for e in health["errors"]:
            print(f"  - {e}")
    if health.get("warnings"):
        print(f"\n{ui.C.YELLOW}警告:{ui.C.END}")
        for w in health["warnings"]:
            print(f"  - {w}")
    print("-" * 78)

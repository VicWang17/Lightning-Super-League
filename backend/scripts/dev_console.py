#!/usr/bin/env python3
"""
One-file developer console for Lightning Super League.

Run from repo root:
    python backend/scripts/dev_console.py

Quick keys:
    1  full reset + create season
    2  status
    3  next matchday
    4  recent results
    5  next event
    6  run season
    7  health check
    q  quit
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
MATCH_ENGINE_URL = os.getenv("MATCH_ENGINE_URL", "http://localhost:8080")
ENGINE_LOG = Path("/private/tmp/lsl-match-engine.log")

# 自动检测 Python 解释器（优先使用虚拟环境）
VENV_PYTHON = BACKEND_DIR / ".venv" / "bin" / "python"
if VENV_PYTHON.exists():
    PYTHON = str(VENV_PYTHON)
else:
    PYTHON = shutil.which("python3") or shutil.which("python") or "python3"


class C:
    BOLD = "\033[1m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    DIM = "\033[2m"
    END = "\033[0m"


def main() -> None:
    while True:
        print_menu()
        choice = input("选择 / key > ").strip().lower()
        if choice in {"q", "quit", "exit", "0"}:
            print("bye")
            return
        try:
            handle_choice(choice)
        except KeyboardInterrupt:
            print_warning("已中断当前操作")
        except Exception as exc:
            print_error(f"操作失败: {exc}")
        input(f"\n{C.DIM}按回车返回菜单...{C.END}")


def print_menu() -> None:
    clear_screen()
    print(f"{C.BOLD}{C.CYAN}Lightning Super League 开发控制台{C.END}")
    print("=" * 52)
    print("  1 / b   一键重置数据 + 创建赛季")
    print("  2 / s   查看当前状态")
    print("  3 / m   跑到下一个比赛日（自动检查/启动引擎）")
    print("  4 / r   查看最近比赛结果")
    print("  5 / n   推进下一个事件")
    print("  6 / a   快进整个赛季")
    print("  7 / h   健康检查")
    print("  8 / e   启动 Go 比赛引擎服务")
    print("  9 / api 启动 FastAPI 后端")
    print("  0 / q   退出")
    print("-" * 52)
    print(f"Repo: {REPO_ROOT}")
    print(f"Engine: {MATCH_ENGINE_URL}")
    print()


def handle_choice(choice: str) -> None:
    if choice in {"1", "b", "boot", "bootstrap"}:
        bootstrap()
    elif choice in {"2", "s", "status"}:
        run_dev_sim("status")
    elif choice in {"3", "m", "matchday"}:
        ensure_engine()
        run_dev_sim("matchday")
    elif choice in {"4", "r", "results"}:
        run_dev_sim("results")
    elif choice in {"5", "n", "next"}:
        run_dev_sim("next-event")
    elif choice in {"6", "a", "all", "season"}:
        ensure_engine()
        run_dev_sim("season")
    elif choice in {"7", "h", "health"}:
        health_check()
    elif choice in {"8", "e", "engine"}:
        ensure_engine(force=True)
    elif choice in {"9", "api", "backend"}:
        print_info("将以前台方式启动 FastAPI 后端；按 Ctrl+C 返回。")
        run([PYTHON, "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"], cwd=BACKEND_DIR)
    else:
        print_warning("未知选项。请输入 1-9，或 q 退出。")


def bootstrap() -> None:
    print_warning("这个操作会删除并重建开发数据库数据。")
    confirm = input("输入 YES 继续 > ").strip()
    if confirm != "YES":
        print_warning("已取消")
        return

    steps = [
        ("启动 MySQL + Redis", ["make", "infra-up"], REPO_ROOT),
        ("重建开发数据库", [PYTHON, "-m", "scripts.reset_dev_db"], BACKEND_DIR),
        ("运行数据库迁移", [PYTHON, "-m", "alembic", "upgrade", "head"], BACKEND_DIR),
        ("初始化基础数据", [PYTHON, "-m", "scripts.init_system"], BACKEND_DIR),
        ("创建并启动赛季", [PYTHON, "-m", "scripts.init_season"], BACKEND_DIR),
    ]
    env = base_env()
    env["ENV"] = "dev"
    env["INIT_SYSTEM_RESET_SCHEMA"] = "false"
    for title, cmd, cwd in steps:
        print_header(title)
        run(cmd, cwd=cwd, env=env)
    print_success("开发数据和赛季准备完成")


def run_dev_sim(command: str) -> None:
    run([PYTHON, "-m", "scripts.dev_sim", command], cwd=BACKEND_DIR, env=base_env())


def health_check() -> None:
    print_header("健康检查")
    run([PYTHON, "-m", "scripts.dev_sim", "status"], cwd=BACKEND_DIR, env=base_env(), check=False)
    print()
    if engine_healthy():
        print_success(f"Go 比赛引擎 OK: {MATCH_ENGINE_URL}")
    else:
        print_warning(f"Go 比赛引擎未响应: {MATCH_ENGINE_URL}")
    print()


def ensure_engine(force: bool = False) -> None:
    if base_env().get("MATCH_ENGINE_TRANSPORT") == "process":
        print_success("开发控制台使用 process 模式，无需启动 8080 服务")
        return

    if not force and engine_healthy():
        print_success("Go 比赛引擎已运行")
        return

    print_header("启动 Go 比赛引擎")
    ENGINE_LOG.parent.mkdir(parents=True, exist_ok=True)
    log = ENGINE_LOG.open("a")
    env = os.environ.copy()
    env.setdefault("GOCACHE", "/private/tmp/go-cache")
    subprocess.Popen(
        ["go", "run", "./cmd/server"],
        cwd=str(REPO_ROOT / "match-engine"),
        env=env,
        stdout=log,
        stderr=log,
        start_new_session=True,
    )
    print_info(f"后台启动中，日志: {ENGINE_LOG}")

    for _ in range(30):
        if engine_healthy():
            print_success("Go 比赛引擎已就绪")
            return
        time.sleep(0.5)

    print_error("Go 比赛引擎没有在 15 秒内就绪。")
    print_info(f"请查看日志: tail -n 80 {ENGINE_LOG}")
    raise RuntimeError("match engine failed to start")


def engine_healthy() -> bool:
    try:
        with urllib.request.urlopen(f"{MATCH_ENGINE_URL}/health", timeout=1.5) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("service") == "match-engine"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None, check: bool = True) -> None:
    print(f"{C.DIM}$ {' '.join(cmd)}{C.END}")
    completed = subprocess.run(cmd, cwd=str(cwd), env=env or base_env())
    if check and completed.returncode != 0:
        raise RuntimeError(f"命令退出码 {completed.returncode}: {' '.join(cmd)}")


def base_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", ".")
    env.setdefault("MATCH_ENGINE_TRANSPORT", "process")
    env.setdefault("MATCH_ENGINE_MODE", "instant")
    env.setdefault("MATCH_ENGINE_FALLBACK_RANDOM", "false")
    return env


def print_header(text: str) -> None:
    print(f"\n{C.BOLD}{C.CYAN}== {text}{C.END}")


def print_success(text: str) -> None:
    print(f"{C.GREEN}✓ {text}{C.END}")


def print_warning(text: str) -> None:
    print(f"{C.YELLOW}! {text}{C.END}")


def print_error(text: str) -> None:
    print(f"{C.RED}x {text}{C.END}")


def print_info(text: str) -> None:
    print(f"{C.CYAN}{text}{C.END}")


def clear_screen() -> None:
    if sys.stdout.isatty():
        os.system("clear")


if __name__ == "__main__":
    main()

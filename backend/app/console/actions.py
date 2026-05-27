from __future__ import annotations

import os
import subprocess

from app.console import ui
from app.console.context import BACKEND_DIR, PYTHON, REPO_ROOT, base_env
from app.services.match_engine_client import get_match_engine_client


def run(cmd: list[str], cwd, env: dict[str, str]) -> None:
    print(f"{ui.C.DIM}$ {' '.join(cmd)}{ui.C.END}")
    completed = subprocess.run(cmd, cwd=str(cwd), env=env)
    if completed.returncode != 0:
        raise RuntimeError(f"command exited with {completed.returncode}: {' '.join(cmd)}")


def bootstrap(yes: bool = False) -> None:
    if not yes:
        ui.warning("这个操作会重建开发数据库数据")
        confirm = input("输入 YES 继续 > ").strip()
        if confirm != "YES":
            ui.warning("已取消")
            return

    env = base_env()
    env["ENV"] = "dev"
    env["INIT_SYSTEM_RESET_SCHEMA"] = "false"

    steps = [
        ("启动 MySQL + Redis", ["make", "infra-up"], REPO_ROOT, os.environ.copy()),
        ("重建开发数据库", [PYTHON, "-m", "scripts.reset_dev_db"], BACKEND_DIR, env),
        ("运行数据库迁移", [PYTHON, "-m", "alembic", "upgrade", "head"], BACKEND_DIR, env),
        ("初始化基础数据", [PYTHON, "-m", "scripts.init_system"], BACKEND_DIR, env),
        ("创建首赛季", [PYTHON, "-m", "scripts.init_season"], BACKEND_DIR, env),
    ]

    for title, cmd, cwd, step_env in steps:
        ui.section(title)
        run(cmd, cwd=cwd, env=step_env)
    ui.success("开发数据已准备完成")


async def engine_health() -> None:
    ok = await get_match_engine_client().health_check()
    if ok:
        ui.success("match engine available")
    else:
        ui.error("match engine unavailable")


async def set_clock(runner, mode: str, speed: float | None) -> None:
    if runner.shared_clock:
        state = await runner.shared_clock.set_mode(mode, speed=speed)
        await runner.db.commit()
        status = await runner.shared_clock.status()
        ui.success(f"clock mode={state.mode} speed={state.speed} now={status['virtual_now']}")
    else:
        runner.clock.set_mode(mode, speed=speed)
        ui.success(f"clock mode={runner.clock.mode} speed={runner.clock.speed}")

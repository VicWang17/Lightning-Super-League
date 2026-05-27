from __future__ import annotations

import os
import shutil
from pathlib import Path

from app.core.clock import clock
from app.dependencies import AsyncSessionLocal
from app.services.game_clock_state import GameClockStateService
from app.services.simulation_runner import SimulationRunner


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / "backend"
VENV_PYTHON = BACKEND_DIR / ".venv" / "bin" / "python"
PYTHON = str(VENV_PYTHON) if VENV_PYTHON.exists() else (shutil.which("python3") or shutil.which("python") or "python3")


def base_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", ".")
    env.setdefault("MATCH_ENGINE_TRANSPORT", "process")
    env.setdefault("MATCH_ENGINE_MODE", "instant")
    env.setdefault("MATCH_ENGINE_FALLBACK_RANDOM", "false")
    return env


async def with_runner(fn):
    async with AsyncSessionLocal() as db:
        runner = SimulationRunner(db, clock, shared_clock=GameClockStateService(db))
        return await fn(runner)

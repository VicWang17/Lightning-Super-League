from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.console import panels, ui
from app.console.context import BACKEND_DIR, REPO_ROOT, PYTHON, base_env
from app.services.simulation_runner import RunnerResult


settings = get_settings()


@dataclass
class StartedProcess:
    name: str
    process: subprocess.Popen
    log_path: Path


@dataclass
class ApiModeContext:
    backend_url: str = field(default_factory=lambda: f"http://localhost:{settings.BACKEND_PORT}")
    frontend_url: str = field(default_factory=lambda: f"http://localhost:{settings.FRONTEND_PORT}")
    started: list[StartedProcess] = field(default_factory=list)

    @property
    def api_url(self) -> str:
        return f"{self.backend_url}/api/v1"

    def ensure_services(self) -> None:
        if not http_ok(f"{self.backend_url}/health/"):
            self.start_backend()
            wait_for(f"{self.backend_url}/health/", "backend")
        if not http_ok(self.frontend_url):
            self.start_frontend()
            wait_for(self.frontend_url, "frontend")

    def start_backend(self) -> None:
        log_path = Path("/private/tmp/lsl-backend-console.log")
        log = log_path.open("a")
        env = base_env()
        cmd = [
            "nohup",
            PYTHON,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(settings.BACKEND_PORT),
        ]
        process = subprocess.Popen(cmd, cwd=str(BACKEND_DIR), env=env, stdout=log, stderr=log, start_new_session=True)
        self.started.append(StartedProcess("backend", process, log_path))
        ui.success(f"started backend, log={log_path}")

    def start_frontend(self) -> None:
        npm = shutil.which("npm") or "npm"
        log_path = Path("/private/tmp/lsl-frontend-console.log")
        log = log_path.open("a")
        env = os.environ.copy()
        env.setdefault("VITE_API_URL", self.api_url)
        cmd = [
            "nohup",
            npm,
            "run",
            "dev",
            "--",
            "--host",
            "0.0.0.0",
            "--port",
            str(settings.FRONTEND_PORT),
        ]
        process = subprocess.Popen(cmd, cwd=str(REPO_ROOT / "frontend"), env=env, stdout=log, stderr=log, start_new_session=True)
        self.started.append(StartedProcess("frontend", process, log_path))
        ui.success(f"started frontend, log={log_path}")

    def cleanup_prompt(self) -> None:
        if not self.started:
            return
        print()
        if not ui.ask_yes_no("是否结束本次 console 自动启动的前后端进程？", default=False):
            return
        for item in self.started:
            terminate_process_group(item)
            ui.success(f"stopped {item.name}")
        self.started.clear()


class ApiClient:
    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip("/")

    def get(self, path: str) -> Any:
        return request_json("GET", f"{self.api_url}{path}")

    def post(self, path: str, body: dict | None = None) -> Any:
        return request_json("POST", f"{self.api_url}{path}", body=body)

    def set_clock(self, mode: str, speed: float | None = None) -> None:
        params = {"mode": mode}
        if speed is not None:
            params["speed"] = str(speed)
        query = urllib.parse.urlencode(params)
        self.post(f"/dev/clock/set-mode?{query}")

    def status(self) -> dict:
        return self.get("/dev/simulation/status")["data"]

    def process_due(self, max_events: int = 200) -> RunnerResult:
        data = self.post("/dev/simulation/process-due", {"max_events": max_events})["data"]
        return RunnerResult(
            processed=data["processed"],
            season_ends=data["season_ends"],
            stopped_reason=data["stopped_reason"],
            results=data["results"],
        )

    def monitor_data(self) -> dict:
        return self.get("/dev/simulation/monitor")["data"]


def http_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1.5) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def wait_for(url: str, name: str, timeout_seconds: float = 30.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if http_ok(url):
            ui.success(f"{name} ready: {url}")
            return
        time.sleep(0.5)
    raise RuntimeError(f"{name} did not become ready: {url}")


def request_json(method: str, url: str, body: dict | None = None) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60.0) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: {exc.code} {detail}") from exc


def terminate_process_group(item: StartedProcess) -> None:
    try:
        os.killpg(os.getpgid(item.process.pid), signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        item.process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(item.process.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass


def watch_api(ctx: ApiModeContext, speed: float, interval_seconds: float, monitor_mode: bool = False) -> None:
    try:
        ctx.ensure_services()
        client = ApiClient(ctx.api_url)
        client.set_clock("turbo", speed)
        iteration = 0
        while True:
            iteration += 1
            result = client.process_due(max_events=200)
            status = client.status()

            if monitor_mode:
                monitor = client.monitor_data()
                panels.render_monitor(
                    status, result, speed, interval_seconds, iteration,
                    standings=monitor.get("standings"),
                    daily_scores=monitor.get("daily_scores"),
                    top_players=monitor.get("top_players"),
                    records=monitor.get("records"),
                    health=monitor.get("health"),
                )
            else:
                panels.render_world(status, result, speed, interval_seconds, iteration)

            time.sleep(max(0.0, interval_seconds))
    finally:
        ctx.cleanup_prompt()

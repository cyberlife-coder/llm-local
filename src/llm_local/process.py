from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .paths import Paths


def is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def current_pid(paths: Paths) -> int | None:
    if not paths.pid_path.exists():
        return None
    try:
        pid = int(paths.pid_path.read_text().strip())
    except ValueError:
        return None
    if is_process_alive(pid):
        return pid
    paths.pid_path.unlink(missing_ok=True)
    return None


def port_is_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def command_for(paths: Paths, model: dict[str, Any]) -> list[str]:
    host = str(model.get("host", "127.0.0.1"))
    port = str(model.get("port", 8000))
    backend = model.get("backend", "vllm_mlx")

    if backend == "mlx_lm":
        # The bundled Anthropic<->OpenAI proxy supervises mlx_lm.server itself,
        # so this stays a single tracked process. Run via the tool's own
        # interpreter so `llm_local.anthropic_proxy` is importable.
        cmd = [
            sys.executable,
            "-m",
            "llm_local.anthropic_proxy",
            "--model",
            str(model["model"]),
            "--host",
            host,
            "--port",
            port,
        ]
        cmd.extend(str(arg) for arg in model.get("args", []))
        return cmd

    cmd = [
        str(paths.vllm_mlx),
        "serve",
        str(model["model"]),
        "--host",
        host,
        "--port",
        port,
    ]
    cmd.extend(str(arg) for arg in model.get("args", []))
    return cmd


def run_vllm_mlx(paths: Paths, args: list[str]) -> int:
    return subprocess.call([str(paths.vllm_mlx), *args], cwd=str(paths.home))


def active_state(paths: Paths) -> dict[str, Any]:
    if not paths.active_path.exists():
        return {}
    try:
        return json.loads(paths.active_path.read_text())
    except json.JSONDecodeError:
        return {}


def start_server(paths: Paths, name: str, model: dict[str, Any]) -> int:
    log_path = paths.log_dir / f"{name}.log"
    cmd = command_for(paths, model)
    env = os.environ.copy()
    env.setdefault("HF_XET_HIGH_PERFORMANCE", "1")

    with log_path.open("ab", buffering=0) as log:
        proc = subprocess.Popen(
            cmd,
            cwd=str(paths.home),
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    paths.pid_path.write_text(str(proc.pid) + "\n")
    paths.active_path.write_text(
        json.dumps(
            {
                "pid": proc.pid,
                "name": name,
                "model": model["model"],
                "host": model.get("host", "127.0.0.1"),
                "port": model.get("port", 8000),
                "log": str(log_path),
                "command": cmd,
                "started_at": int(time.time()),
            },
            indent=2,
        )
        + "\n"
    )
    return proc.pid


def stop_server(paths: Paths, timeout_seconds: float = 6.0) -> int | None:
    pid = current_pid(paths)
    if not pid:
        return None
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not is_process_alive(pid):
            paths.pid_path.unlink(missing_ok=True)
            return pid
        time.sleep(0.2)
    raise SystemExit(f"PID {pid} did not stop after SIGTERM.")


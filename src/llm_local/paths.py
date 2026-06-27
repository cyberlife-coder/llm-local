from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    home: Path
    config_path: Path
    models_dir: Path
    state_dir: Path
    log_dir: Path
    pid_path: Path
    active_path: Path
    vllm_mlx: Path | str


def default_home() -> Path:
    if env_home := os.environ.get("LLM_LOCAL_HOME"):
        return Path(env_home).expanduser()
    return Path.home() / ".local" / "share" / "llm-local"


def resolve_paths() -> Paths:
    home = default_home()
    config_path = Path(os.environ.get("LLM_LOCAL_CONFIG", home / "models.json")).expanduser()
    models_dir = Path(os.environ.get("LLM_LOCAL_MODELS_DIR", home / "models")).expanduser()
    state_dir = Path(os.environ.get("LLM_LOCAL_STATE_DIR", home / "state")).expanduser()
    log_dir = Path(os.environ.get("LLM_LOCAL_LOG_DIR", home / "logs")).expanduser()
    vllm_mlx = os.environ.get("LLM_LOCAL_VLLM_MLX")
    if vllm_mlx is None:
        local_bin = home / ".venv" / "bin" / "vllm-mlx"
        vllm_mlx = local_bin if local_bin.exists() else "vllm-mlx"
    return Paths(
        home=home,
        config_path=config_path,
        models_dir=models_dir,
        state_dir=state_dir,
        log_dir=log_dir,
        pid_path=state_dir / "server.pid",
        active_path=state_dir / "active.json",
        vllm_mlx=vllm_mlx,
    )


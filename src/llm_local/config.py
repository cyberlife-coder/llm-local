from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import Paths
from .templates import default_config


def ensure_layout(paths: Paths) -> None:
    paths.home.mkdir(parents=True, exist_ok=True)
    paths.models_dir.mkdir(parents=True, exist_ok=True)
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    paths.log_dir.mkdir(parents=True, exist_ok=True)
    paths.config_path.parent.mkdir(parents=True, exist_ok=True)
    if not paths.config_path.exists():
        save_config(paths, default_config(str(paths.models_dir)))


def load_config(paths: Paths) -> dict[str, Any]:
    ensure_layout(paths)
    try:
        return json.loads(paths.config_path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON config at {paths.config_path}: {exc}") from exc


def save_config(paths: Paths, config: dict[str, Any]) -> None:
    paths.config_path.write_text(json.dumps(config, indent=2) + "\n")


def model_config(paths: Paths, name: str | None) -> tuple[str, dict[str, Any]]:
    config = load_config(paths)
    model_name = name or config.get("default_model")
    models = config.get("models", {})
    if model_name not in models:
        names = ", ".join(sorted(models)) or "(none)"
        raise SystemExit(f"Unknown model '{model_name}'. Available: {names}")
    return model_name, models[model_name]


def local_model_dir(paths: Paths, name: str) -> Path:
    return paths.models_dir / name


def manifest_path(path: Path) -> Path:
    return path / "vllm_mlx_model_manifest.json"


def read_manifest(path: Path) -> dict[str, Any] | None:
    manifest = manifest_path(path)
    if not manifest.exists():
        return None
    try:
        return json.loads(manifest.read_text())
    except json.JSONDecodeError:
        return None


def model_local_path(paths: Paths, name: str, model: dict[str, Any]) -> Path | None:
    configured = Path(str(model.get("model", ""))).expanduser()
    if configured.is_absolute():
        return configured
    candidate = local_model_dir(paths, name)
    return candidate if manifest_path(candidate).exists() else None


def is_downloaded(paths: Paths, name: str, model: dict[str, Any]) -> bool:
    path = model_local_path(paths, name, model)
    return bool(path and manifest_path(path).exists())


def source_for(model: dict[str, Any]) -> str:
    return str(model.get("source") or model["model"])


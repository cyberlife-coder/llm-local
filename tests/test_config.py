from __future__ import annotations

from llm_local.config import is_downloaded, load_config
from llm_local.paths import resolve_paths


def test_default_config_uses_env_home(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_LOCAL_HOME", str(tmp_path))

    paths = resolve_paths()
    config = load_config(paths)

    assert paths.home == tmp_path
    assert config["default_model"] == "qwen36-a3b-64k"
    assert "qwen36-a3b-262k" in config["models"]


def test_download_status_requires_manifest(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_LOCAL_HOME", str(tmp_path))
    paths = resolve_paths()
    config = load_config(paths)
    model = config["models"]["qwen36-a3b"]

    assert not is_downloaded(paths, "qwen36-a3b", model)

    model_dir = paths.models_dir / "qwen36-a3b"
    model_dir.mkdir(parents=True)
    (model_dir / "vllm_mlx_model_manifest.json").write_text("{}")

    assert is_downloaded(paths, "qwen36-a3b", model)


def test_download_status_recognizes_mlx_lm_dir(monkeypatch, tmp_path):
    # mlx_lm / hf downloads have config.json + safetensors but no vllm manifest.
    monkeypatch.setenv("LLM_LOCAL_HOME", str(tmp_path))
    paths = resolve_paths()
    model_dir = paths.models_dir / "some-mlx-model"
    model_dir.mkdir(parents=True)
    model = {"model": str(model_dir), "backend": "mlx_lm"}

    assert not is_downloaded(paths, "some-mlx-model", model)
    (model_dir / "config.json").write_text("{}")
    assert is_downloaded(paths, "some-mlx-model", model)


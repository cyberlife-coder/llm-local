from __future__ import annotations

import pytest

from llm_local.cli import build_parser, local_launch_env, main


def test_parser_has_expected_commands():
    parser = build_parser()
    help_text = parser.format_help()

    assert "doctor" in help_text
    assert "profiles" in help_text
    assert "qwen36-a3b-64k" in help_text


def test_no_args_prints_practical_help(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("LLM_LOCAL_HOME", str(tmp_path))

    main([])

    out = capsys.readouterr().out
    assert "Daily flow:" in out
    assert "llm-local doctor" in out


def test_unknown_model_exits_cleanly(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_LOCAL_HOME", str(tmp_path))

    with pytest.raises(SystemExit):
        main(["serve", "missing-model"])


def test_local_launch_env_isolates_and_targets_local_server(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_LOCAL_HOME", str(tmp_path))
    # Inherited credentials must not leak into the local launch.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "real-cloud-key")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "real-cloud-token")

    from llm_local.paths import resolve_paths

    paths = resolve_paths()
    env, base_url, served = local_launch_env(paths)

    # Default profile is qwen36-a3b-64k on port 8003, served name "default".
    assert base_url == "http://127.0.0.1:8003"
    assert served == "default"
    assert env["ANTHROPIC_BASE_URL"] == base_url
    assert env["ANTHROPIC_MODEL"] == "default"
    # No token override: Claude Code keeps its own defaults.
    assert "CLAUDE_CODE_MAX_OUTPUT_TOKENS" not in env
    # Cloud credentials dropped; isolated config dir set.
    assert "ANTHROPIC_API_KEY" not in env
    assert "ANTHROPIC_AUTH_TOKEN" not in env
    assert env["CLAUDE_CONFIG_DIR"] == str(tmp_path / "claude-local")

    settings = (tmp_path / "claude-local" / "settings.json").read_text()
    assert "apiKeyHelper" in settings


def test_mlx_lm_backend_builds_proxy_command(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_LOCAL_HOME", str(tmp_path))

    from llm_local.paths import resolve_paths
    from llm_local.process import command_for

    paths = resolve_paths()
    model = {
        "model": "/models/supergemma",
        "host": "127.0.0.1",
        "port": 8006,
        "backend": "mlx_lm",
        "args": ["--max-tokens", "32768"],
    }
    cmd = command_for(paths, model)
    assert cmd[1:3] == ["-m", "llm_local.anthropic_proxy"]
    assert "--model" in cmd and "/models/supergemma" in cmd
    assert "8006" in cmd
    assert cmd[-2:] == ["--max-tokens", "32768"]
    # vllm-mlx must NOT be invoked for an mlx_lm profile
    assert "serve" not in cmd



def test_add_serve_arg_appends_to_profile(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_LOCAL_HOME", str(tmp_path))
    from llm_local.config import load_config
    from llm_local.paths import resolve_paths

    main([
        "add", "mymodel", "mlx-community/Some-Model",
        "--backend", "mlx_lm", "--port", "9001",
        "--serve-arg=--chat-template-args",
        "--serve-arg", '{"enable_thinking": false}',
    ])
    config = load_config(resolve_paths())
    args = config["models"]["mymodel"]["args"]
    assert args[-2:] == ["--chat-template-args", '{"enable_thinking": false}']
    assert config["models"]["mymodel"]["backend"] == "mlx_lm"


def test_profile_status_list(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_LOCAL_HOME", str(tmp_path))
    from llm_local.cli import profile_status_list
    from llm_local.paths import resolve_paths

    items = profile_status_list(resolve_paths())
    names = [n for n, _, _ in items]
    assert "qwen36-a3b-64k" in names
    assert all(downloaded is False for _, _, downloaded in items)  # nothing in tmp


def test_claude_local_model_flag_parses():
    parser = build_parser()
    args = parser.parse_args(["claude-local", "--model", "foo"])
    assert args.model == "foo"


def test_claude_local_no_server_non_interactive_exits(monkeypatch, tmp_path):
    # No running server, no --model, and pytest stdin is not a tty -> clean exit.
    monkeypatch.setenv("LLM_LOCAL_HOME", str(tmp_path))
    with pytest.raises(SystemExit):
        main(["claude-local"])


def test_fit_label():
    from llm_local.cli import fit_label, usable_gpu_gb
    # 64 GB -> ~48 GB usable by the GPU; fits if <=42, tight if <=48, else too big
    assert usable_gpu_gb(64) == 48.0
    assert fit_label(13, 64) == "fits"
    assert fit_label(45, 64) == "tight"
    assert fit_label(56, 64) == "too big"
    assert fit_label(70, 64) == "too big"
    assert fit_label(None, 64) == "size ?"
    assert fit_label(13, None) == "size ?"


def test_machine_ram_gb_positive():
    from llm_local.cli import machine_ram_gb
    ram = machine_ram_gb()
    assert ram is None or ram > 0


def test_remote_size_local_path_is_none():
    from llm_local.cli import remote_size_gb
    assert remote_size_gb("/Users/x/models/foo") is None  # local path, no network

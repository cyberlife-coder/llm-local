# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`llm-local` is a thin, dependency-free CLI wrapper around `vllm-mlx` for running
local OpenAI/Anthropic-compatible LLM servers on Apple Silicon. It does no
inference itself — it manages model profiles, shells out to `vllm-mlx` for
downloads and serving, tracks one running server via PID/state files, and prints
env vars to point clients (including Claude Code) at the local endpoint.

## Commands

```bash
uv pip install -e ".[test]"   # dev install (uses uv venv; see CONTRIBUTING.md)
pytest                        # run all tests
pytest tests/test_cli.py::test_no_args_prints_practical_help   # run a single test
python -m llm_local --version # smoke-check the package entry point
```

There is no configured linter/formatter in the repo. Tests are configured in
`pyproject.toml` (`pythonpath = ["src"]`, `testpaths = ["tests"]`).

## Architecture

The package lives in `src/llm_local/` (src-layout). Data flows in one direction:
`templates → config → paths → process`, with `cli` orchestrating everything.

- **`paths.py`** — `resolve_paths()` is the single source of truth for *where*
  everything lives. All locations derive from `LLM_LOCAL_HOME`
  (default `~/.local/share/llm-local`) and can each be overridden by env var
  (`LLM_LOCAL_CONFIG`, `LLM_LOCAL_MODELS_DIR`, `LLM_LOCAL_VLLM_MLX`, etc.).
  Returns an immutable `Paths` dataclass. Tests rely on `LLM_LOCAL_HOME` pointing
  at a tmp dir for full isolation.
- **`templates.py`** — pure data. `default_config()` builds the initial
  `models.json` (the three `qwen36-a3b-*` agent profiles) and `agent_args()`
  assembles the `vllm-mlx serve` flag list for a given context/output size. Edit
  profile defaults here, not in generated config.
- **`config.py`** — reads/writes `models.json` and resolves model entries.
  `ensure_layout()` creates dirs and writes default config on first use (called
  implicitly by `load_config`). Download status is determined *solely* by the
  presence of `vllm_mlx_model_manifest.json` in the model dir (see
  `is_downloaded`/`manifest_path`) — there is no separate download registry.
- **`process.py`** — process lifecycle. A single server is tracked by two files
  in `state/`: `server.pid` (liveness via `os.kill(pid, 0)`) and `active.json`
  (the running model's name/host/port/log/command). `start_server` launches
  `vllm-mlx serve` detached (`start_new_session=True`) with stdout/stderr
  redirected to `logs/<name>.log`. Only one server at a time.
- **`cli.py`** — argparse subcommands. Each `cmd_*` calls `configured_paths()`
  (which resolves paths + ensures layout) then delegates to the modules above.
  `main()` with no args prints the practical guide (`cmd_help`).
- **`anthropic_proxy.py`** — bundled stdlib Anthropic↔OpenAI bridge for the
  `mlx_lm` backend (see below). Pure translation functions
  (`anthropic_to_openai_request`, `openai_to_anthropic_response`,
  `StreamTranslator`) are unit-tested in `tests/test_proxy.py`.

### Backends

A profile's optional `"backend"` field selects the serving engine:

- **`vllm_mlx`** (default) — `command_for` builds a `vllm-mlx serve …` command.
  vllm-mlx natively exposes both OpenAI and Anthropic APIs.
- **`mlx_lm`** — for models vllm-mlx can't serve (e.g. text-only quants of
  multimodal archs like gemma4). `command_for` instead launches
  `python -m llm_local.anthropic_proxy`, which supervises an
  `mlx_lm.server` child (OpenAI-only) and fronts it with an Anthropic
  `/v1/messages` bridge + OpenAI passthrough on the public port. So a single
  tracked PID serves both APIs, and `claude-local`/`env-*` work unchanged.
  mlx_lm is invoked via `uvx --from mlx-lm mlx_lm.server` (override with
  `LLM_LOCAL_MLX_LM`); unknown profile `args` are forwarded to the child
  (e.g. `--chat-template-args '{"enable_thinking": false}'` to suppress a
  reasoning model's thought channel so it answers directly).

## Conventions & invariants

- **No runtime dependencies.** `pyproject.toml` `dependencies = []` is
  deliberate — keep it that way. Only stdlib (`argparse`, `json`, `subprocess`,
  `socket`, `signal`, `pathlib`). Test-only dep is `pytest`.
- **Errors use `raise SystemExit(message)`**, not custom exceptions or
  `sys.exit()` scattered around. Follow this for new failure paths.
- **Network safety:** profiles bind `127.0.0.1` by default. `cmd_serve` refuses
  `0.0.0.0` unless `--allow-network` is passed. Preserve this guard.
- **Don't change the user's global shell/env.** `claude-local` and `env-*`
  commands scope the local endpoint to one invocation only; normal `claude`
  stays on Anthropic. Keep changes opt-in and explicit (see CONTRIBUTING.md).
- **Tests must not download models or run real inference.** They exercise config
  and CLI behavior only, isolated via `LLM_LOCAL_HOME` → tmp_path. The
  `vllm-mlx` binary is never invoked in tests.
- The `served-model-name` for every profile is `default` — clients use model
  name `default` regardless of which profile is serving.

# Changelog

## Unreleased

- Add an `mlx_lm` backend (per-profile `backend` field) for models vllm-mlx
  can't serve, e.g. text-only quants of multimodal architectures.
- Bundle a zero-dependency Anthropic↔OpenAI proxy (`llm_local.anthropic_proxy`)
  that supervises `mlx_lm.server` and exposes both APIs on one port, so
  `claude-local` works with `mlx_lm`-backed models.
- Optionally surface reasoning models' thinking as Anthropic `thinking` blocks
  (`--expose-reasoning`).
- `claude-local` now uses an isolated `CLAUDE_CONFIG_DIR` + `apiKeyHelper` (never
  touches a claude.ai login, no key-approval prompt) and targets the served
  model name.
- `add --backend`, and backend-aware `list`/`profiles`/`doctor`.

## 0.1.0

- Initial public-ready package structure.
- Add `llm-local` console script.
- Add portable runtime home via `LLM_LOCAL_HOME`.
- Add model profile management for local `vllm-mlx` servers.
- Add Qwen3.6 A3B agent profiles: 64k, 128k, and 262k.
- Add OpenAI-compatible and Anthropic-compatible environment helpers.
- Add `doctor`, `profiles`, `cache`, `pull`, `serve`, `restart`, `status`, and log commands.
- Add unit tests for config and CLI behavior.


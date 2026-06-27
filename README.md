# llm-local

`llm-local` is a small CLI for running local `vllm-mlx` servers on Apple Silicon.
It manages model profiles, downloads MLX model artifacts, starts/stops a local
OpenAI-compatible endpoint, and prints temporary environment variables for
OpenAI-style clients or Claude Code-compatible Anthropic-style clients.

The project is intentionally boring: a thin, inspectable wrapper around
`vllm-mlx` with no Python runtime dependencies.

**Which model to run?** See [evals/MODELS.md](evals/MODELS.md) for the recommended
set and copy-paste setup. The picks come from two benchmarks on an Apple M5 Pro
(64 GB): [BENCHMARKS.md](BENCHMARKS.md) (broad ~10-model speed screen) and
[evals/](evals/) (deep, judged quality over 50 scenarios — current results in
[evals/LEADERBOARD.md](evals/LEADERBOARD.md)).

## Status

Alpha. It works for local development, but profile defaults should be treated as
starting points rather than universal performance claims.

## Requirements

- macOS on Apple Silicon
- Python 3.11+
- `uv`, `pipx`, or another Python installer
- `vllm-mlx` installed somewhere on `PATH`, or `LLM_LOCAL_VLLM_MLX` set

Install the runtime in a dedicated home if you want a self-contained setup:

```bash
mkdir -p ~/.local/share/llm-local
cd ~/.local/share/llm-local
uv venv
source .venv/bin/activate
uv pip install vllm-mlx
```

## Install

From a local checkout:

```bash
uv tool install -e .
```

For development:

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[test]"
```

## Quick Start

```bash
llm-local init
llm-local doctor
llm-local list
llm-local pull qwen36-a3b
llm-local serve qwen36-a3b-64k
```

The default profile serves:

```text
http://127.0.0.1:8003/v1
```

with model name:

```text
default
```

## Agent Profiles

The generated config includes three Qwen3.6 A3B profiles:

| Profile | Context | Default output | Max requested output | Port | Use case |
| --- | ---: | ---: | ---: | ---: | --- |
| `qwen36-a3b-64k` | 65,536 | 16,384 | 16,384 | 8003 | Default Claude-like agent profile |
| `qwen36-a3b-128k` | 131,072 | 16,384 | 32,768 | 8002 | Larger repositories and longer sessions |
| `qwen36-a3b-262k` | 262,144 | 32,768 | 65,536 | 8004 | Long-context experiments |

Long context is not automatically better. Large contexts increase latency and
memory pressure, and agent quality often depends more on context curation than
raw window size.

## Connect Clients

For OpenAI-compatible clients:

```bash
eval "$(llm-local env-openai)"
```

For Anthropic-compatible clients:

```bash
eval "$(llm-local env-anthropic)"
```

For Claude Code only in this shell invocation:

```bash
llm-local claude-local
```

Normal `claude` remains untouched unless you explicitly run `llm-local
claude-local`.

## Commands

```bash
llm-local                 # practical guide
llm-local -h              # compact CLI help
llm-local doctor          # runtime/config/port checks
llm-local list            # configured profiles
llm-local profiles        # context/output profile summary
llm-local cache           # local model cache
llm-local inspect MODEL   # inspect via vllm-mlx
llm-local pull MODEL      # download a configured model
llm-local serve [MODEL]   # start server
llm-local restart [MODEL] # restart server
llm-local stop            # stop server
llm-local status          # endpoint and PID
llm-local logs [MODEL]    # server logs
```

## Other backends: `mlx_lm`

Some models can't be served by `vllm-mlx` — notably text-only quants of
multimodal architectures (for example a text-only `gemma4` build). Such a model
can use the `mlx_lm` backend instead: it runs under `mlx_lm.server` and is
fronted by a small bundled proxy so the public port still speaks **both** the
OpenAI and Anthropic APIs, which means `llm-local claude-local` keeps working.

```bash
llm-local add supergemma Jiunsong/supergemma4-26b-uncensored-mlx-4bit-v2 \
  --backend mlx_lm --local --port 8006 --pull
llm-local serve supergemma
llm-local claude-local
```

`mlx_lm` is launched via `uvx --from mlx-lm mlx_lm.server` (override with
`LLM_LOCAL_MLX_LM`). Unknown profile `args` are forwarded straight to
`mlx_lm.server`, e.g. `--chat-template-args '{"enable_thinking": false}'`.

### Reasoning ("thinking") models

By default the proxy drops the model's reasoning channel so it answers directly.
To surface it as Anthropic `thinking` blocks instead, add `--expose-reasoning`
to the profile `args` (and keep thinking enabled in the chat template).

## Configuration

By default, `llm-local` stores state under:

```text
~/.local/share/llm-local
```

Override it with:

```bash
export LLM_LOCAL_HOME=/path/to/runtime
```

Other useful overrides:

```bash
export LLM_LOCAL_CONFIG=/path/to/models.json
export LLM_LOCAL_MODELS_DIR=/path/to/models
export LLM_LOCAL_VLLM_MLX=/path/to/vllm-mlx
```

## Security Notes

Profiles bind to `127.0.0.1` by default. The CLI refuses profiles that bind to
`0.0.0.0` unless you pass `--allow-network`.

No API key is configured by default. If you expose the server beyond localhost,
add an API key in the profile args and understand the network risk.

## NVIDIA NVFP4 on Mac

NVIDIA `NVFP4` / ModelOpt checkpoints are intended for CUDA vLLM on NVIDIA
hardware. On Apple Silicon, prefer MLX artifacts such as
`mlx-community/Qwen3.6-35B-A3B-4bit`.

## Development

```bash
uv pip install -e ".[test]"
pytest
python -m llm_local --version
```


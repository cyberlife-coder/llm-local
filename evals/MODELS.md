# Recommended models & setup

The curated set that came out of the [eval](EVAL_RESULTS.md), for an Apple Silicon
Mac with ~64 GB. Each is a plain causal-LM served through `llm-local`'s `mlx_lm`
backend (so `claude-local` works), except Qwen3.6 which uses `vllm_mlx`.

| Use it for | Model | Backend | tok/s |
|---|---|---|--:|
| **Daily driver** (best value) | SuperGemma4-26B | mlx_lm | 63 |
| **Best code/debug/agent quality** | Qwen3-Coder-Next-80B | mlx_lm | 21 |
| **Fastest generalist** | Qwen3.6-35B-A3B | vllm_mlx | 85 |
| **Hermes-style agent** | Hermes-4-14B | mlx_lm | 32 |

## One-time setup

`Qwen3.6-35B-A3B` ships in the default config (`llm-local init`). Add the rest:

```bash
# SuperGemma is a reasoning model — pass enable_thinking:false for direct, fast
# answers (--serve-arg appends flags to the profile; use ARG=VALUE for dashed ones):
llm-local add supergemma4-26b Jiunsong/supergemma4-26b-uncensored-mlx-4bit-v2 \
  --backend mlx_lm --local --port 8006 --pull \
  --serve-arg=--chat-template-args --serve-arg '{"enable_thinking": false}'
llm-local add qwen3-coder-next-80b mlx-community/Qwen3-Coder-Next-4bit \
  --backend mlx_lm --local --port 8014 --pull
llm-local add hermes4-14b mlx-community/Hermes-4-14B-4bit \
  --backend mlx_lm --local --port 8013 --pull
```

> **Reasoning models** think before answering, which is slow and the thinking is
> dropped by default. The `--serve-arg` above disables it for direct answers. To
> instead *keep* the thinking and surface it as Anthropic `thinking` blocks, add a
> second profile with `--serve-arg=--expose-reasoning` (see the main README).

## Use a model

```bash
llm-local claude-local               # if nothing is running, shows a menu to
                                     # pick + auto-start a model, then opens Claude Code
# or do it explicitly:
llm-local serve supergemma4-26b      # start a profile (one at a time)
llm-local status                     # endpoint + PID
eval "$(llm-local env-openai)"       # point OpenAI-compatible tools at it
```

To switch models, `llm-local stop` then `serve` another — memory only holds one.

## Verify

```bash
llm-local doctor                     # runtime + every profile's backend/state/port
```

Both backends expose **OpenAI** (`/v1/chat/completions`) **and Anthropic**
(`/v1/messages`) on the served port, so the same server works for OpenAI tools and
for Claude Code.

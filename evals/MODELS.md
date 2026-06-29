# Recommended models & setup

The curated set from the **v3.0** [eval](EVAL_RESULTS.md) (M5 Pro / 64 GB,
2026-06-29), filtered by a hard **>30 tok/s decode floor** for interactive use.
Each is served through `llm-local`'s `mlx_lm` backend (so `claude-local` works),
except Qwen3.6-A3B which uses `vllm_mlx`. See [LEADERBOARD.md](LEADERBOARD.md) for
the numbers behind these picks.

| Use it for | Model | Backend | quant | tok/s |
|---|---|---|---|--:|
| **Agentic coding / debug** (quality) | Ornith-1.0-35B | mlx_lm | 6bit | 60 |
| **Daily driver** (best value, reasoning) | SuperGemma4-26B unc | mlx_lm | 4bit | 65 |
| **Fastest generalist** (+think for math) | Qwen3.6-35B-A3B | vllm_mlx | 4bit | 87 |
| **Heavyweight code/agent** (alt) | Qwen3-Coder-Next-80B | mlx_lm | 4bit | 61 |
| **Max correctness** (small, slower) | Hermes-4-14B | mlx_lm | 4bit | 31 |

> **Thinking vs no-think:** every reasoning model ships a `<name>` (thinking-off,
> fast/direct) and a `<name>-think` (thinking-on, reasoning exposed) profile.
> **Turn thinking ON** for weak-reasoner models (Qwen3.6-A3B: math pass-rate 62→88%)
> and hard Rust/algorithm tasks; **leave it OFF** for the already-strong models
> (SuperGemma, Ornith, Hermes) — there it only adds ~3× latency and can truncate.
> Dropped after v3.0: GLM-4.7-Flash (good only with slow thinking), Nemotron-3-Nano
> (dominated by Ornith), and dense 24-27B coders (below the speed floor).

## One-time setup

`Qwen3.6-35B-A3B` ships in the default config (`llm-local init`). Add the rest:

```bash
# Reasoning models — pass enable_thinking:false for direct, fast answers
# (--serve-arg appends flags to the profile; use ARG=VALUE for dashed ones):
llm-local add ornith-35b mlx-community/Ornith-1.0-35B-6bit \
  --backend mlx_lm --local --port 8020 --pull \
  --serve-arg=--chat-template-args --serve-arg '{"enable_thinking": false}'
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

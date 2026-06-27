# Benchmarks

> ⚠️ **Read this as machine- and stack-specific, not as universal model rankings.**
> Numbers are decode throughput on one Mac with one serving stack, on a specific
> date. They will differ on other hardware, quantizations, and engines.

## Test machine

| | |
|---|---|
| Chip | Apple **M5 Pro** |
| Unified memory | **64 GB** |
| OS | macOS 26.5.1 (build 25F80) |
| Date of run | June 2026 |
| Free disk during run | ~250–390 GB |

## How models were served

- **`llm-local`** (this tool) for the local models, in one of two backends:
  - `vllm_mlx` — `Qwen3.6-35B-A3B` (native OpenAI + Anthropic endpoints).
  - `mlx_lm` — the other local models, via the bundled Anthropic proxy + `mlx_lm.server`.
  - All local models are **4-bit MLX** quants.
- **ollama 0.30.11** for the ollama-managed models (its OpenAI-compatible endpoint on `:11434`); these use ollama's own quant (one is NVFP4).
- **One model loaded at a time** (64 GB cap). Measurements were taken **after all
  downloads finished**, so disk I/O did not contend with inference.

## Metrics

All requests go through each engine's **OpenAI-compatible** `/v1/chat/completions`
(uniform across `llm-local` and ollama), `temperature=0`.

- **Speed (tok/s)** — decode throughput = `completion_tokens / wall_time` on a
  fixed ~300-token generation, non-streaming, **best of 2 after one warm-up**.
  This is decode throughput only — **not** time-to-first-token or prompt processing.
- **Quality** — three probes, judged by a Claude model reading the raw outputs:
  - **Coding**: a `merge_intervals(intervals)` function — correct iff it sorts,
    merges overlaps, and handles empty/unsorted input (`max_tokens=600`).
  - **Tool-calling**: an OpenAI `get_weather` tool + a prompt that should call it —
    pass iff a correct `tool_call` is emitted (`max_tokens=300`).
  - **Frontend/design**: a self-contained responsive pricing section in HTML/CSS —
    judged for valid CSS, structure, responsiveness, and polish (`max_tokens=1100`).

## Results

| Model (repo) | Served via | Type | tok/s | Coding | Tool-call | Frontend | Kept? |
|---|---|---|---:|:--:|:--:|---|:--:|
| Qwen3.6-35B-A3B-4bit | llm-local · vllm-mlx | 35B / 3B MoE | **84.9** | ✅ | ✅ | clean | ✅ |
| Qwen3-Coder-30B-A3B-Instruct-4bit | llm-local · mlx_lm | 30B / 3B MoE | 71.3 | ✅ | ✅ | ⚠️ invalid CSS (`rounded:`, broken meta) | ✅ |
| SuperGemma4-26B-uncensored-mlx-4bit | llm-local · mlx_lm | 26B / 4B MoE | 62.9 | ✅ | ✅ | clean | ✅ |
| Hermes-4-14B-4bit | llm-local · mlx_lm | 14B dense | 32.0 | ✅ | ✅ | responsive (`@media`) | ✅ |
| gemma4:12b | ollama | 12B dense | 26.1 | ✅ | ✅ | ⚠️ thin (~1.5 KB) | ✖ |
| Qwen3-Coder-Next-4bit | llm-local · mlx_lm | 80B / 3B MoE | 21.5 | ✅ | ✅ | 🥇 excellent (badge, hover-lift, icons) | ✅ |
| Devstral-Small-2-24B-2512-4bit | llm-local · mlx_lm | 24B dense | 20.4 | ✅ | ❌ no tool-call¹ | clean | ✖ |
| Dolphin-Mistral-24B-Venice-4bit | llm-local · mlx_lm | 24B dense | 20.3 | ✅ | ❌ no tool-call¹ | clean | ✖ |
| qwen3.6:27b-coding-nvfp4 | ollama | 27B | 14.5 | ⚠️ reasoning² | ✅ | clean | ✖ |
| Hermes-4-70B-4bit | llm-local · mlx_lm | 70B dense | **5.6** | ⚠️ reasoning² | ✅ | responsive | ✖ |

¹ Tool-calling reflects the **serving stack** (`mlx_lm.server`'s OpenAI tool parsing).
Mistral-family models did not surface `tool_calls` here — a stack limitation, not
necessarily a model incapability.
² Reasoning models spent the 600-token coding budget "thinking" and emitted no final
code in this probe; their coding quality is **unmeasured** here — the practical
signal is latency-to-answer.

## Verdicts (for these use cases, on this machine)

- **Code (Claude Code / OpenCode)** — needs speed + correctness + reliable tool-calls:
  **Qwen3.6-35B-A3B** (85 tok/s) or **Qwen3-Coder-30B-A3B** (71 tok/s).
- **Hermes-style agent** — **Hermes-4-14B** (32 tok/s, tool-calls work). Hermes-4-70B
  has the higher ceiling but **5.6 tok/s is unusable interactively**.
- **OpenDesign / front-end** — **Qwen3-Coder-Next-80B** for quality (clean, polished
  UI); **SuperGemma-26B** (63 tok/s) for fast iteration.

## Takeaways for 64 GB Apple Silicon

- **MoE models with few active params (A3B/A4B) dominate**: 60–85 tok/s vs 5–20 tok/s
  for dense models of similar or larger size — decisive for interactive agent loops.
- **Avoid dense ≥70B and reasoning models for interactive use** — too slow to a final
  answer.
- **Tool-calling is stack-dependent**: Qwen/Hermes surfaced tool calls through
  `mlx_lm.server`; Mistral-family did not (in this setup).

## Caveats

Decode throughput only; best-of-2 (indicative, not a rigorous benchmark); mixed
quantizations across engines; single short prompt per metric; quality probes are
small and judged subjectively. Treat as a practical screening, not a leaderboard.

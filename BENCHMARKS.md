# Benchmarks

> ⚠️ **Read this as machine- and stack-specific, not as universal model rankings.**
> Numbers are decode throughput on one Mac with one serving stack, on a specific
> date. They will differ on other hardware, quantizations, and engines.

> **Two layers — read them together:**
> - **This file** = a broad **speed** screen of ~10 models (one short prompt per
>   quality dimension). Use it to compare **throughput** and shortlist.
> - **[evals/](evals/)** = a deep, **judged quality** comparison of the kept models
>   over 50 scenarios with a reproducible protocol — see
>   [evals/LEADERBOARD.md](evals/LEADERBOARD.md) (current: suite **v2.0**).
>   Where the two differ on quality, **evals wins** (more scenarios, larger budgets,
>   rubric-based judging). In particular the single-prompt **design** column below
>   was truncation-limited; the v2.0 eval shows design is a near-3-way tie.
>
> **v3.0 (2026-06-29)** re-ran everything on an idle machine, added new June-2026
> models, and applied a hard **>30 tok/s decode floor** for interactive use. Of the
> models screened, **5 were kept** (see [evals/MODELS.md](evals/MODELS.md)):
> **Ornith-1.0-35B** (new), SuperGemma4-26B, Qwen3-Coder-Next-80B, Qwen3.6-35B-A3B,
> Hermes-4-14B. Dropped: **Qwen3.6-27B** (dense, 16.7 tok/s — below floor),
> GLM-4.7-Flash and Nemotron-3-Nano (underdelivered), plus the v2.0 retirees.
> A stale v2.0 number was corrected: **Coder-Next-80B decodes at ~61 tok/s, not 21**
> (the old figure was contaminated by concurrent downloads).

## Test machine

| | |
|---|---|
| Chip | Apple **M5 Pro** |
| Unified memory | **64 GB** |
| OS | macOS 26.5.1 (build 25F80) |
| Date of run | 2026-06-29 (v3.0) |
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

Decode tok/s (best-of-2, ~300-token gen, idle machine), with the deterministic
objective pass-rate (math+business) and Rust compile-rate from the v3.0 eval. The
`+think` columns are the same model run thinking-on (see [the leaderboard](evals/LEADERBOARD.md)).

| Model (quant) | Served via | Type | tok/s | obj | Rust /6 | obj +think | Kept? |
|---|---|---|---:|:--:|:--:|:--:|:--:|
| Qwen3.6-35B-A3B (4bit) | llm-local · vllm-mlx | 35B / 3B MoE | **86.6** | 62% | 4 | 88% | ✅ |
| SuperGemma4-26B unc (4bit) | llm-local · mlx_lm | 26B / 4B MoE | 65.5 | 88% | 4 | 88% | ✅ |
| Qwen3.6-35B-A3B (8bit) | llm-local · vllm-mlx | 35B / 3B MoE | 61.8 | 62% | 4 | 88% | ✖ (no gain vs 4bit) |
| Qwen3-Coder-Next-80B (4bit) | llm-local · mlx_lm | 80B / 3B MoE | 61.2 | 88% | 4 | — | ✅ |
| Nemotron-3-Nano-30B-A3B (8bit) | llm-local · mlx_lm | 31B / 3B MoE | 61.0 | 75% | 3 | 75% | ✖ |
| Ornith-1.0-35B (6bit) | llm-local · mlx_lm | 35B MoE | 59.5 | 88% | **5** | 62%² | ✅ |
| GLM-4.7-Flash (8bit) | llm-local · mlx_lm | 31B / 3B MoE | 43.5 | 50% | 2 | **100%** | ✖ |
| Hermes-4-14B (4bit) | llm-local · mlx_lm | 14B dense | 31.0 | **100%** | **6** | 75%² | ✅ |
| Qwen3.6-27B (4bit) | llm-local · mlx_lm | 27B dense | **16.7** | — | — | — | ✖ below floor |

² Thinking **regressed** for these already-strong models: verbose reasoning overflowed
the 3× answer budget and truncated the final answer. They are best run **no-think**.

## Verdicts (for these use cases, on this machine)

- **Agentic coding / debug (quality)** — **Ornith-1.0-35B** (60 tok/s, 88% obj, 5/6
  Rust, native tool-calling, 262k ctx) or **Qwen3-Coder-Next-80B** (61 tok/s, best
  agentic plans).
- **Daily driver (best value)** — **SuperGemma4-26B** uncensored (65 tok/s, 88% obj).
- **Fastest generalist** — **Qwen3.6-35B-A3B** (87 tok/s); **turn thinking ON** for
  math/architecture (objective 62 → 88%).
- **Max correctness, small** — **Hermes-4-14B** (100% obj, 6/6 Rust) — but 31 tok/s,
  the slowest kept model.

## Takeaways for 64 GB Apple Silicon

- **A >30 tok/s decode floor eliminates dense ≥24B models.** Qwen3.6-27B (16.7) and
  Devstral-class (~20) fail it; only **MoE with ~3B active params** clears it
  comfortably (60–87 tok/s). Decode is memory-bandwidth-bound — total resident size
  matters, so even an 80B/3B MoE (61 tok/s) beats a 24B dense (~20).
- **Thinking is conditional**: it unlocks weak reasoners (GLM 50→100%, Qwen3.6-A3B
  62→88%) and helps Rust, but does nothing for already-strong models and can regress
  them via truncation. Cost ≈ 3× tokens to an answer.
- **Higher quant ≠ better**: 8-bit Qwen3.6-A3B matched 4-bit quality at −27% speed.
- **Tool-calling is stack-dependent**: Qwen/Hermes surfaced tool calls through
  `mlx_lm.server`; Mistral-family did not (in this setup).

## Caveats

Decode throughput only; best-of-2 (indicative, not a rigorous benchmark); mixed
quantizations across engines; single short prompt per metric; quality probes are
small and judged subjectively. Treat as a practical screening, not a leaderboard.

# Leaderboard

Append-only. One section per suite version. Scores are comparable **only within
the same suite version and machine class**. See [PROTOCOL.md](PROTOCOL.md) for how
rows are produced and [EVAL_RESULTS.md](EVAL_RESULTS.md) for the breakdown.

## Suite v2.0 — Apple M5 Pro / 64 GB — 2026-06  ← current

v2.0 raised per-scenario output budgets (design 1500→3200, etc.) to remove the
truncation that had depressed scores — especially design. Overall = mean of the 8
category judge scores (/10). Speed = decode tok/s. (`qwen3-coder-30b` was retired
after v1.1; `hermes-4-14b` not re-run.)

| Model | Engine | Overall | tok/s | code | cplx | debug | arch | design | math | biz | agent |
|---|---|:--:|--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **Qwen3-Coder-Next-4bit** (80B/3B) | llm-local mlx_lm | **8.11** | 21.5 | 8.3 | 8.0 | 8.6 | 7.3 | 7.0 | 8.5 | 8.5 | 8.7 |
| **SuperGemma4-26B** (26B/4B) | llm-local mlx_lm | **7.86** | 62.9 | 7.7 | 6.4 | 7.6 | 8.7 | 7.2 | 9.0 | 8.5 | 7.8 |
| **Qwen3.6-35B-A3B** (35B/3B) | llm-local vllm_mlx | 7.41 | 84.9 | 8.1 | 6.3 | 8.2 | 7.2 | 7.2 | 7.0 | 8.0 | 7.2 |

Objective auto-grade pass-rate (math+business, deterministic): 80b 88 %,
SuperGemma 88 %, Qwen3.6-A3B 62 %.

**Reading it (v2.0):**
- **Qwen3-Coder-Next-80B** is the clear quality leader (5/8 categories, best at
  code/complex/debug/agentic) — but **slowest (21 tok/s)**.
- **SuperGemma4-26B** is the best value: wins reasoning (math/architecture), ties
  design, **3× faster, 3× smaller**, and the **only model that never truncated**.
- **Qwen3.6-35B-A3B** is the fastest (85 tok/s) and clean on standard tasks, but
  ships subtle bugs under load (a rate limiter silently disabled by a misused
  `@wraps`, a deadlocking connection pool — both caught by running the code).
- **Design is now a ~3-way tie (7.0–7.2)** — the v1.1 design ranking was a
  truncation artifact. With room to finish, the 80B writes the most polished UIs
  (gradient SVG fills, numeric-aware sorting) but still truncated 2/6; SuperGemma
  finished all 6.

## Suite v1.1 — Apple M5 Pro / 64 GB — 2026-06  (superseded by v2.0)

Tighter token budgets caused widespread truncation (esp. design). Kept for history.

| Model | Engine | Overall | tok/s | code | cplx | debug | arch | design | math | biz | agent |
|---|---|:--:|--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Qwen3-Coder-Next-4bit (80B/3B) | llm-local mlx_lm | 7.82 | 21.5 | 8.9 | 7.7 | 9.8 | 6.3 | 5.2 | 7.5 | 8.5 | 8.7 |
| SuperGemma4-26B (26B/4B) | llm-local mlx_lm | 7.70 | 62.9 | 7.4 | 6.1 | 8.8 | 7.0 | 5.7 | 9.5 | 8.5 | 8.5 |
| Qwen3.6-35B-A3B (35B/3B) | llm-local vllm_mlx | 6.99 | 84.9 | 8.4 | 6.6 | 8.4 | 5.8 | 4.5 | 7.0 | 8.0 | 7.2 |
| Qwen3-Coder-30B-A3B (30B/3B) | llm-local mlx_lm | 5.39 | 71.3 | 5.7 | 4.8 | 6.4 | 5.2 | 5.3 | 6.0 | 6.0 | 3.7 |

<!-- Add new suite versions or machines as new sections above. -->

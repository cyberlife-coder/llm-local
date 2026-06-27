# Leaderboard

Append-only. One row per (model, suite version, machine). Scores are comparable
**only within the same suite version and machine class**. See
[PROTOCOL.md](PROTOCOL.md) for how rows are produced and [EVAL_RESULTS.md](EVAL_RESULTS.md)
for the full per-category / per-scenario breakdown of the seed run.

## Suite v1.1 — Apple M5 Pro / 64 GB — 2026-06

Overall = mean of the 8 category judge scores (/10). Speed = decode tok/s.

| Model | Engine | Overall | tok/s | code | cplx | debug | arch | design | math | biz | agent |
|---|---|:--:|--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **Qwen3-Coder-Next-4bit** (80B/3B) | llm-local mlx_lm | **7.82** | 21.5 | 8.9 | 7.7 | 9.8 | 6.3 | 5.2 | 7.5 | 8.5 | 8.7 |
| **SuperGemma4-26B** (26B/4B) | llm-local mlx_lm | **7.70** | 62.9 | 7.4 | 6.1 | 8.8 | 7.0 | 5.7 | 9.5 | 8.5 | 8.5 |
| **Qwen3.6-35B-A3B** (35B/3B) | llm-local vllm_mlx | 6.99 | 84.9 | 8.4 | 6.6 | 8.4 | 5.8 | 4.5 | 7.0 | 8.0 | 7.2 |
| Qwen3-Coder-30B-A3B (30B/3B) | llm-local mlx_lm | 5.39 | 71.3 | 5.7 | 4.8 | 6.4 | 5.2 | 5.3 | 6.0 | 6.0 | 3.7 |

**Reading it:** highest quality = Qwen3-Coder-Next-80B (but slowest). Best
value = SuperGemma4-26B (≈same quality, 3× faster, 3× smaller). Fastest
generalist = Qwen3.6-35B-A3B. Qwen3-Coder-30B trails on every category.

<!-- Add new rows below. Keep the same columns and note the suite version + machine. -->

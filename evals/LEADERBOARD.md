# Leaderboard

Append-only. One section per suite version. Scores are comparable **only within
the same suite version and machine class**. See [PROTOCOL.md](PROTOCOL.md) for how
rows are produced and [EVAL_RESULTS.md](EVAL_RESULTS.md) for the breakdown.

## Suite v3.0 — Apple M5 Pro / 64 GB — 2026-06-29  ← current

v3.0 adds **6 Rust scenarios** (compile-checked with `rustc` via
[rust_check.py](rust_check.py)), a hard interactive **decode-speed floor of
>30 tok/s** (slower models are dropped for interactive use), and benchmarks every
reasoning model in **both thinking and no-think** modes. The columns here are the
**reproducible objective backbone**: decode tok/s (best-of-2, idle machine), the
deterministic math+business pass-rate ([grade.py](grade.py)), and the Rust
compile-rate — plus the thinking-mode delta. Subjective categories (design /
architecture / agentic prose) were spot-judged, not fully re-scored, so no single
"Overall /10" is given (unlike v2.0); rank on the axis that matches your use.

| Model (quant) | Engine | tok/s | obj math+biz | Rust /6 | obj +think | Rust +think |
|---|---|--:|--:|:--:|--:|:--:|
| **Ornith-1.0-35B** (35B MoE, 6bit) | mlx_lm | 59.5 | 88% | 5 | 62%* | **6** |
| **Qwen3-Coder-Next-80B** (80B/3B, 4bit) | mlx_lm | 61.2 | 88% | 4 | — | — |
| **SuperGemma4-26B** unc (26B/4B, 4bit) | mlx_lm | 65.5 | 88% | 4 | 88% | 5 |
| **Qwen3.6-35B-A3B** (35B/3B, 4bit) | vllm_mlx | **86.6** | 62% | 4 | **88%** | 4 |
| **Hermes-4-14B** (14B dense, 4bit) | mlx_lm | 31.0 | **100%** | **6** | 75%* | 5 |
| Nemotron-3-Nano-30B-A3B (31B/3B, 8bit) | mlx_lm | 61.0 | 75% | 3 | 75% | **6** |
| GLM-4.7-Flash (31B/3B, 8bit) | mlx_lm | 43.5 | 50% | 2 | **100%** | 4 |
| Qwen3.6-35B-A3B (8bit variant) | vllm_mlx | 61.8 | 62% | 4 | 88% | 4 |
| Qwen3.6-27B (dense, 4bit) | mlx_lm | **16.7** | — | — | — | — |

`*` thinking **regressed** here via budget-overflow truncation (verbose reasoning
ate the answer budget at 3× budget) — these models are best run **no-think**.
Qwen3.6-27B is listed last: at 16.7 tok/s it is **below the >30 floor** and dropped
for interactive use despite strong reported SWE-bench scores (a 24-27B *dense*
model is memory-bandwidth-bound on this machine; only few-active-param MoEs clear
the floor).

**Reading it (v3.0):**
- **Speed floor reshaped the field.** Every kept model is a **MoE with ~3B active
  params** (fast decode) or the small Hermes dense; the **dense 24-27B coders**
  (Qwen3.6-27B 16.7, and Devstral-class ~20 from v2.0) **fail the floor** regardless
  of quality. Corrected a stale v2.0 number: **Coder-Next-80B is 61 tok/s, not 21**
  (the old figure was contaminated by concurrent downloads).
- **Thinking is conditional, not free.** It **unlocks the weak reasoners**
  (GLM-4.7-Flash 50→100%, Qwen3.6-A3B 62→88%) and **improves Rust** broadly, but
  **does nothing for already-strong models and can regress them** (Ornith 88→62%,
  Hermes 100→75%) by overflowing the budget. Cost ≈ **3× tokens** (latency-to-answer).
  Use it for weak-reasoner + hard-algo/Rust tasks; stay no-think otherwise.
- **Quant: 8-bit bought nothing.** Qwen3.6-A3B 8-bit matched its 4-bit objective
  (62%) and Rust (4/6) while being **27% slower** (61.8 vs 86.6) → **4-bit preferred**
  for A3B MoEs. Ornith 6-bit is a sensible middle.
- **New models:** **Ornith-1.0-35B is the standout addition** (best Rust + tool-calling
  + 262k ctx, ~60 tok/s); GLM-4.7-Flash and Nemotron underdeliver vs research hype on
  this suite (GLM only with slow thinking; Nemotron dominated by Ornith).

## Suite v2.0 — Apple M5 Pro / 64 GB — 2026-06  (superseded by v3.0)

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

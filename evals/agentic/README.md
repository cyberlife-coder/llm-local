# Agentic eval suite

A reproducible, objective-first benchmark for **agentic local-coding use**
(Claude Code / OpenCode / Hermes-style tool agents), complementary to the
category suite in [`../scenarios.json`](../scenarios.json). It scores a model on
four axes that matter for an agent loop — and most are graded **automatically**
(code is executed / compiled), not by an LLM judge.

Built and first run on 2026-06-29/30 (Apple M5 Pro / 64 GB) to settle
**Ornith-1.0-35B vs Qwen3.6-A3B**. See findings at the bottom.

## What it measures

| Axis | Files | Grading |
|---|---|---|
| **Code correctness** (20 exercises: ML/transformers, Python stdlib & process, concurrency & protocols, Rust, data transforms) | `scenarios_personal.json` | objective — `grade_personal.py` runs the Python and compiles the Rust (`rustc --crate-type lib`) |
| **Agentic convergence** (does it fix its own errors given feedback?) | `repair_loop.py` | objective — feeds the compiler/test error back, up to N rounds, records rounds-to-pass or "did not converge" |
| **Tool-calling** (8 scenarios: single call, selection, arg/enum extraction, abstention, parallel, 2-turn `tool_result` chaining) | `tool_call_test.py` | objective — inspects the Anthropic `/v1/messages` response for valid `tool_use` blocks |
| **Cowork / agent planning** (3 Hermes-style plans: incident debug, migration, tool-orchestration) | `scenarios_cowork.json` | judged by reading the saved outputs |
| **Performance** (decode tok/s, latency, thinking overhead) | `speed_probe.py`, `task_runner.py` | objective timing |

`task_runner.py` also builds a full **Kanban app** (CRUD + HTML5 drag-and-drop +
localStorage) — a realistic single-file app generation, used to compare code
quality across models/modes.

## Running it

Models are served one at a time by `llm-local` (memory holds one). At
`temperature=0` outputs are deterministic, so results are load-independent
(only the *speed* numbers need an idle machine).

```bash
# One profile, no-think:
./run_suite.sh ornith-35b 8020 nothink
# One profile, thinking (Anthropic path, reasoning kept separate):
./run_suite.sh ornith-35b-think 8028 think

# Grade the objective half:
python3 grade_personal.py ornith-35b

# Agentic convergence (serve a profile first, then):
python3 repair_loop.py ornith-35b http://127.0.0.1:8020 default 3

# Kanban app build + 350-word speed check:
python3 task_runner.py ornith-35b http://127.0.0.1:8020 10000 0
```

### Trust the grader first

`grade_personal.py` is self-validated: `build_gold.py` writes reference
solutions to `out/_gold/`, and grading them must score **17/17** before any
model run is trusted.

```bash
python3 build_gold.py && python3 grade_personal.py _gold   # expect 17/17
```

## Scripts

- `run_personal.py` — run the 20 exercises (OpenAI endpoint, no-think).
- `run_think.py` — run scenarios via the **Anthropic** endpoint in thinking mode
  (reads `thinking` vs `text` blocks separately; budget is a CLI arg).
- `run_subset.py` — re-run specific scenario ids at raised budgets
  (`scenarios_rerun*.json`) to separate "can't" from "didn't fit in budget".
- `grade_personal.py` — objective grader (Python exec + `rustc` compile),
  multi-candidate code extraction.
- `build_gold.py` — reference solutions, for self-testing the grader.
- `repair_loop.py` — iterative self-repair / convergence test.
- `tool_call_test.py` — tool-calling on `/v1/messages`.
- `speed_probe.py` — fresh decode tok/s probe (standardized prompt, best-of-N).
- `task_runner.py` — Kanban app build (+ 350-word speed check).
- `run_suite.sh` — convenience driver for one profile.

Output goes to `out/<label>/` and `out_kanban/` (git-ignored — regenerate locally).

## Findings (Ornith vs A3B, 2026-06-30)

- **Decode speed is mode-independent**: A3B ~97 tok/s, Ornith ~65 tok/s, the same
  with or without thinking. Thinking doesn't slow tokens — it generates ~8× more
  of them (reasoning), so latency goes from ~8 s to ~30–95 s per task.
- **No-think is the agentic default.** Both converge ~16/17 within 3 feedback
  rounds and tool-call 8/8 (no-think). Thinking adds latency + truncation for no
  objective gain in the loop; Ornith-think can even crash at 32k output (KV OOM).
- **A3B-think truncates real apps** (8k config cap → broken Kanban). A3B *no-think*
  is fine. Ornith one-shots more correct code; A3B is rattlable in an iterating loop.
- Net: **Ornith-35B (no-think) is the agentic driver** (correct code + tool-calling
  + 262k context); A3B no-think is the fast lightweight alternative.

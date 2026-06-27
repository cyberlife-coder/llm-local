# Eval protocol (the reproducible standard)

This defines how to benchmark **any** model with this suite so results are
comparable over time. The goal: a stable, versioned procedure you can re-run on a
new model and append to the [leaderboard](LEADERBOARD.md).

## Invariants (don't change these per-run)

1. **Suite is versioned and frozen.** `scenarios.json` has `meta.version`. A given
   version's prompts, token budgets, and rubrics never change. Improvements ship as
   a **new version** (e.g. 2.0); scores are only comparable **within the same
   version**.
2. **Deterministic generation.** `temperature = 0`, one sample per scenario, each
   scenario's own `max_tokens`, via the OpenAI `/v1/chat/completions` endpoint.
3. **One model at a time**, no concurrent load (so speed is measurable and memory
   isn't contended). Engine-agnostic: anything exposing an OpenAI endpoint
   (`llm-local`'s `vllm_mlx` or `mlx_lm` backend, ollama, etc.).
4. **Record the context.** Every scorecard states `suite_version`, `engine`,
   `machine` (chip + RAM), and `date`. Results are only comparable within the same
   `(suite_version, machine-class)`.

## Procedure

```bash
# 1. Serve the model (one at a time)
llm-local serve <profile>            # or any OpenAI-compatible server

# 2. Generate all 50 outputs
python3 evals/run.py <label> http://127.0.0.1:<port> default
#    -> evals/out/<label>/<id>.txt  (+ _timings.tsv for tok/s)

# 3. Auto-grade the objective subset (deterministic)
python3 evals/grade.py evals/out
```

## Scoring (two layers)

**A. Objective auto-grade — deterministic, reproducible.**
Scenarios with an `expected` field (verifiable math/business answers) are graded by
`grade.py`: pass iff every `expected` group has at least one alternative present in
the output. This is a **coarse presence check** — sensitive to truncation and
phrasing, and it does **not** verify reasoning (a model can state a right number it
didn't actually derive). Use it as a smoke signal, not the final word.

**B. Judge score — authoritative quality, per category.**
For each of the 8 categories, an independent LLM judge scores every model's output
**0–10 against that scenario's `rubric`**, reading the raw text. Use a capable model
as judge. Truncated/incomplete outputs are penalized. Recommended judge prompt:

> You are an impartial expert judge for the "<category>" category. For each scenario
> (from `scenarios.json`, that category only), read the candidate outputs at
> `evals/out/<label>/<id>.txt` and score each 0–10 **strictly against the scenario's
> `rubric`**. For code, trace correctness and edge cases; for design (HTML), check
> completeness/validity and required elements; for agentic, judge plan order and
> safeguards. Penalize truncation. Return JSON: per-scenario scores + a per-category
> average + a one-line rationale each.

> ℹ️ Why two layers: in suite v1.x the model with the **highest** auto-grade pass-rate
> was the **worst** when judged (it stated some right numbers but produced broken code
> and out-of-order agent plans). The judge layer is what reflects real quality.

## Scorecard (append one per model)

Each run produces a row appended to [`LEADERBOARD.md`](LEADERBOARD.md):

```
| model | suite | engine | machine | date | overall /10 | tok/s | per-category… | objective % |
```

A machine-readable scorecard (optional) follows this schema:

```json
{
  "model": "mlx-community/Qwen3-Coder-Next-4bit",
  "suite_version": "1.1",
  "engine": "llm-local mlx_lm",
  "machine": "Apple M5 Pro / 64GB",
  "date": "2026-06-27",
  "tok_s": 21.5,
  "category_scores": {"coding": 8.86, "debugging": 9.8, "...": 0},
  "overall": 7.82,
  "objective_passrate": 0.62
}
```

## Adding a new model

```bash
llm-local add <name> <hf-repo-id> --backend mlx_lm --local --port <port> --pull
# (reasoning models: append --chat-template-args '{"enable_thinking": false}'
#  to the profile args in models.json for direct answers)
llm-local serve <name>
python3 evals/run.py <name> http://127.0.0.1:<port> default
python3 evals/grade.py evals/out
# run the judge prompt per category, then append a row to LEADERBOARD.md
```

That's the whole standard: **freeze the suite, generate at temp 0 one-at-a-time,
auto-grade the objective subset, judge the rest against the rubrics, append a dated
scorecard.**

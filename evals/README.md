# Model eval suite

A concrete, reproducible comparison of local models for real developer/work
sessions, across 8 categories.

- **[`scenarios.json`](scenarios.json)** — versioned suite: 50 scenarios across 8
  categories. Each has a `prompt`, a token budget, a `rubric`, and (for verifiable
  math/business) an `expected` answer.
- **[`PROTOCOL.md`](PROTOCOL.md)** — the reproducible standard: how to run, grade,
  and judge any model so results stay comparable over time.
- **[`LEADERBOARD.md`](LEADERBOARD.md)** — append-only results table (seeded with 4
  models). Add a row when you benchmark a new model.
- **[`MODELS.md`](MODELS.md)** — the recommended model set + copy-paste setup.
- **[`EVAL_RESULTS.md`](EVAL_RESULTS.md)** — full per-category / per-scenario
  breakdown of the seed run, with a recommendation by session type.
- **[`run.py`](run.py)** — runs the suite against any OpenAI-compatible endpoint.
- **[`grade.py`](grade.py)** — deterministic auto-grader for the objective subset.

## Reproduce

```bash
# serve a model (one at a time), then run the suite against its endpoint:
llm-local serve supergemma4-26b
python3 evals/run.py supergemma4-26b http://127.0.0.1:8006 default
# outputs land in evals/out/<label>/<id>.txt
```

## Judging

`math` and `business` scenarios have **verifiable answers** (e.g. break-even =
6250 units, RICE order B>A>C>D, 100! → 24 trailing zeros) — grade on the correct
final answer and completeness. The other categories were scored by LLM judges
against each scenario's rubric; truncated outputs are penalized. See
[`EVAL_RESULTS.md`](EVAL_RESULTS.md) for the methodology and caveats.

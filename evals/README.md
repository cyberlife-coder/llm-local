# Model eval suite

A concrete, reproducible comparison of local models for real developer/work
sessions, across 8 categories.

- **[`scenarios.json`](scenarios.json)** — 50 scenarios (coding, coding_complex,
  debugging, architecture, design, math, business, agentic). Each has a `prompt`,
  a token budget, and a `rubric`.
- **[`EVAL_RESULTS.md`](EVAL_RESULTS.md)** — judged results for 4 models on an
  Apple M5 Pro (64 GB), with per-category and per-scenario scores and a
  recommendation by session type.
- **[`run.py`](run.py)** — runner that executes the suite against any
  OpenAI-compatible endpoint.

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

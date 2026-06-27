#!/usr/bin/env python3
"""Deterministic auto-grader for the objective subset of the eval suite.

Scenarios that carry an `expected` field (math/business with verifiable answers)
are graded WITHOUT an LLM: a scenario passes iff, for every group in `expected`,
at least one alternative string appears (case-insensitive) in the model output.

Usage:
    python3 evals/grade.py <results_root>

<results_root> contains one subdir per model label, each with <id>.txt files
(this is what evals/run.py writes to evals/out/). Prints a pass-rate table.

This is a heuristic presence check (it verifies the answer shows up, not the full
reasoning); the subjective categories are scored by the judge protocol in
PROTOCOL.md. It exists so the objective core of the benchmark is reproducible
and engine-agnostic.
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def passes(output: str, expected: list[list[str]]) -> bool:
    low = output.lower()
    return all(any(alt.lower() in low for alt in group) for group in expected)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: grade.py <results_root>")
    root = pathlib.Path(sys.argv[1])
    scenarios = json.loads((HERE / "scenarios.json").read_text())["scenarios"]
    graded = [s for s in scenarios if "expected" in s]
    labels = sorted(p.name for p in root.iterdir() if p.is_dir())
    if not labels:
        sys.exit(f"no model dirs in {root}")

    print(f"Auto-graded objective scenarios ({len(graded)}): "
          + ", ".join(s["id"] for s in graded))
    print()
    width = max(len(l) for l in labels)
    print(f"{'model'.ljust(width)}  pass/total  detail")
    results = {}
    for label in labels:
        rows = []
        ok = 0
        for s in graded:
            f = root / label / f"{s['id']}.txt"
            text = f.read_text() if f.exists() else ""
            p = passes(text, s["expected"])
            ok += p
            rows.append(f"{s['id']}={'Y' if p else 'n'}")
        results[label] = ok / len(graded)
        print(f"{label.ljust(width)}  {ok}/{len(graded)}        {' '.join(rows)}")
    print()
    print("objective score (pass-rate):")
    for label, rate in sorted(results.items(), key=lambda kv: -kv[1]):
        print(f"  {label.ljust(width)}  {rate*100:.0f}%")


if __name__ == "__main__":
    main()

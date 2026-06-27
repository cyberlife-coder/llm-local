#!/usr/bin/env python3
"""Run the eval suite (scenarios.json) against an OpenAI-compatible endpoint.

Stdlib only. Saves each output to out/<label>/<id>.txt and a timings TSV.

Example:
    llm-local serve supergemma4-26b
    python3 evals/run.py supergemma4-26b http://127.0.0.1:8006 default

Then judge the outputs (objective categories like math/business have verifiable
answers; the rest were scored by LLM judges — see EVAL_RESULTS.md).
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent


def chat(base: str, model: str, content: str, max_tokens: int):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
        "temperature": 0,
    }).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/v1/chat/completions",
        data=body, headers={"Content-Type": "application/json"},
    )
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.loads(r.read())
    ct = (d.get("usage") or {}).get("completion_tokens") or 0
    return (d["choices"][0]["message"].get("content") or ""), time.monotonic() - t0, ct


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit("usage: run.py <label> <base_url> <model_id>")
    label, base, model = sys.argv[1], sys.argv[2], sys.argv[3]
    out = HERE / "out" / label
    out.mkdir(parents=True, exist_ok=True)
    scenarios = json.loads((HERE / "scenarios.json").read_text())["scenarios"]
    with (out / "_timings.tsv").open("w") as tf:
        for s in scenarios:
            try:
                text, dt, ct = chat(base, model, s["prompt"], s["max_tokens"])
            except Exception as exc:  # noqa: BLE001
                text, dt, ct = f"[ERROR: {exc}]", 0, 0
            (out / f"{s['id']}.txt").write_text(text)
            tf.write(f"{s['id']}\t{dt:.1f}\t{ct}\n")
            tf.flush()
            print(f"  {label} {s['id']}: {ct} tok {dt:.1f}s", flush=True)
    print(f"### {label} complete -> {out}")


if __name__ == "__main__":
    main()

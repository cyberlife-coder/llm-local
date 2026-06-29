#!/usr/bin/env python3
"""Run the personal-20 suite against one OpenAI-compatible endpoint.

Usage: run_personal.py <label> <base_url> <model_id> [budget_mult]
Saves outputs to out/<label>/<id>.txt and a timings TSV. Stdlib only.
"""
from __future__ import annotations
import json, pathlib, sys, time, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
SCEN = HERE / "scenarios_personal.json"


def chat(base, model, content, max_tokens):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
        "temperature": 0,
    }).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/v1/chat/completions",
        data=body, headers={"Content-Type": "application/json"})
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=900) as r:
        d = json.loads(r.read())
    ct = (d.get("usage") or {}).get("completion_tokens") or 0
    return (d["choices"][0]["message"].get("content") or ""), time.monotonic() - t0, ct


def main():
    if len(sys.argv) not in (4, 5):
        sys.exit("usage: run_personal.py <label> <base_url> <model_id> [budget_mult]")
    label, base, model = sys.argv[1:4]
    mult = float(sys.argv[4]) if len(sys.argv) == 5 else 1.0
    out = HERE / "out" / label
    out.mkdir(parents=True, exist_ok=True)
    scen = json.loads(SCEN.read_text())["scenarios"]
    with (out / "_timings.tsv").open("w") as tf:
        for s in scen:
            try:
                text, dt, ct = chat(base, model, s["prompt"], int(s["max_tokens"] * mult))
            except Exception as exc:  # noqa: BLE001
                text, dt, ct = f"[ERROR: {exc}]", 0, 0
            (out / f"{s['id']}.txt").write_text(text)
            tf.write(f"{s['id']}\t{dt:.1f}\t{ct}\n"); tf.flush()
            print(f"  {label} {s['id']}: {ct} tok {dt:.1f}s", flush=True)
    print(f"### {label} complete -> {out}", flush=True)


if __name__ == "__main__":
    main()

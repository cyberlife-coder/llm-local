#!/usr/bin/env python3
"""Re-run a subset of scenarios at raised budgets, overwriting out/<label>/<id>.txt.
Usage: run_subset.py <label> <base_url> <model_id> <id1,id2,...> [scenarios_file]
Budgets come from the scenarios file (default scenarios_rerun.json). Stdlib only.
"""
from __future__ import annotations
import json, pathlib, sys, time, urllib.request
HERE = pathlib.Path(__file__).resolve().parent
_SCEN_FILE = sys.argv[5] if len(sys.argv) > 5 else "scenarios_rerun.json"
SCEN = {s["id"]: s for s in json.loads((HERE / _SCEN_FILE).read_text())["scenarios"]}

def chat(base, model, content, max_tokens):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": content}],
                       "max_tokens": max_tokens, "temperature": 0}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/v1/chat/completions",
                                 data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1200) as r:
        d = json.loads(r.read())
    ct = (d.get("usage") or {}).get("completion_tokens") or 0
    return (d["choices"][0]["message"].get("content") or ""), ct

def main():
    label, base, model, ids = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
    out = HERE / "out" / label
    for sid in ids:
        s = SCEN[sid]
        try:
            text, ct = chat(base, model, s["prompt"], s["max_tokens"])
        except Exception as exc:  # noqa: BLE001
            text, ct = f"[ERROR: {exc}]", 0
        (out / f"{sid}.txt").write_text(text)
        print(f"  RERUN {label} {sid}: {ct}/{s['max_tokens']} tok", flush=True)

if __name__ == "__main__":
    main()

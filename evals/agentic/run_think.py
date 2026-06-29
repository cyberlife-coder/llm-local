#!/usr/bin/env python3
"""Run scenarios against the ANTHROPIC /v1/messages endpoint in thinking mode.

This is the path Claude Code / OpenCode / Hermes actually use: reasoning comes
back as separate `thinking` blocks and the answer as `text` blocks. We save the
`text` answer to out/<label>/<id>.txt (so the existing grader works), the
`thinking` to <id>.think.txt, and per-scenario timing + token/char split for the
performance analysis. Budget is min(scenario_max*3, 8000) — equal cap for both
models (A3B-think is configured at 8192), fair for a thinking comparison.

Usage: run_think.py <label> <base_url> <scenarios_file> [ids|ALL] [cap]
"""
from __future__ import annotations
import json, pathlib, sys, time, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
CAP = int(sys.argv[5]) if len(sys.argv) > 5 else 8000


def messages(base, content, max_tokens):
    body = json.dumps({"model": "default", "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": content}]}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/v1/messages", data=body,
                                 headers={"Content-Type": "application/json",
                                          "anthropic-version": "2023-06-01", "x-api-key": "local"})
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=1200) as r:
        d = json.loads(r.read())
    dt = time.monotonic() - t0
    blocks = d.get("content") or []
    think = " ".join(b.get("thinking", "") for b in blocks if isinstance(b, dict) and b.get("type") == "thinking")
    answer = "".join(b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text")
    out_tok = (d.get("usage") or {}).get("output_tokens") or 0
    return answer, think, dt, out_tok, d.get("stop_reason")


def main():
    label, base, scen_file = sys.argv[1], sys.argv[2], sys.argv[3]
    scen = json.loads((HERE / scen_file).read_text())["scenarios"]
    ids = ({s["id"] for s in scen} if (len(sys.argv) <= 4 or sys.argv[4] == "ALL")
           else set(sys.argv[4].split(",")))
    out = HERE / "out" / label
    out.mkdir(parents=True, exist_ok=True)
    with (out / "_timings_think.tsv").open("a") as tf:
        for s in scen:
            if s["id"] not in ids:
                continue
            budget = CAP  # full ceiling; model stops at end_turn when done
            try:
                ans, think, dt, ot, stop = messages(base, s["prompt"], budget)
            except Exception as exc:  # noqa: BLE001
                ans, think, dt, ot, stop = f"[ERROR: {exc}]", "", 0, 0, "error"
            (out / f"{s['id']}.txt").write_text(ans)
            (out / f"{s['id']}.think.txt").write_text(think)
            tf.write(f"{s['id']}\t{dt:.1f}\t{ot}\t{len(think)}\t{len(ans)}\t{stop}\n")
            tf.flush()
            print(f"  {label} {s['id']}: {ot} out-tok {dt:.1f}s think={len(think)}c ans={len(ans)}c stop={stop}", flush=True)
    print(f"### {label} ({scen_file}) complete", flush=True)


if __name__ == "__main__":
    main()

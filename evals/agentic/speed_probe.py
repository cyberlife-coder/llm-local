#!/usr/bin/env python3
"""Fresh controlled decode-speed probe on the Anthropic /v1/messages path.

Standardized decode-bound prompt, warm-up + N timed runs. Reports per-run and
best (max tok/s) + median latency. For thinking profiles also splits thinking
vs answer chars so we see how much of the time is reasoning.

Usage: speed_probe.py <label> <base_url> <budget> <runs>
"""
from __future__ import annotations
import json, statistics as st, sys, time, urllib.request

PROMPT = ("Explain in detail how TCP congestion control works. Cover slow start, "
          "congestion avoidance, the AIMD principle, fast retransmit, and fast recovery, "
          "and how the congestion window evolves over time. Write roughly 350 words of clear prose.")


def call(base, max_tokens):
    body = json.dumps({"model": "default", "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": PROMPT}]}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/v1/messages", data=body,
                                 headers={"Content-Type": "application/json",
                                          "anthropic-version": "2023-06-01", "x-api-key": "local"})
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=1200) as r:
        d = json.loads(r.read())
    dt = time.monotonic() - t0
    blocks = d.get("content") or []
    think = sum(len(b.get("thinking", "")) for b in blocks if b.get("type") == "thinking")
    ans = sum(len(b.get("text", "")) for b in blocks if b.get("type") == "text")
    ot = (d.get("usage") or {}).get("output_tokens") or 0
    return dt, ot, think, ans, d.get("stop_reason")


def main():
    label, base, budget, runs = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    print(f"\n## {label} (budget={budget})", flush=True)
    try:
        call(base, 8)  # warm-up
    except Exception as exc:  # noqa: BLE001
        print(f"  warm-up failed: {exc}"); return
    runs_data = []
    for i in range(runs):
        dt, ot, think, ans, stop = call(base, budget)
        tps = ot / dt if dt else 0
        runs_data.append((dt, ot, tps, think, ans))
        print(f"  run{i+1}: {dt:5.1f}s  {ot:5d} tok  {tps:5.1f} tok/s  (think={think}c ans={ans}c {stop})", flush=True)
    dts = [r[0] for r in runs_data]; tpss = [r[2] for r in runs_data]
    print(f"  => best {max(tpss):.1f} tok/s | median latency {st.median(dts):.1f}s | "
          f"avg out {sum(r[1] for r in runs_data)/len(runs_data):.0f} tok", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Iterative self-repair test: measures whether a model CONVERGES to a working
solution given its own error feedback (the agentic-loop metric), not first-shot.

For one served model, iterate over all objective (py/rust) scenarios:
  - grade the current saved answer (out/<label>/<id>.txt)
  - if it passes -> rounds=0 (already correct first-shot)
  - else feed back [original prompt, its previous code, the exact error] and ask
    for a corrected complete solution; regrade; repeat up to MAX_ROUNDS.
Records rounds-to-converge, or 'DNC' (did not converge).

Repaired attempts are saved to out/<label>/repair/<id>.r<n>.txt (originals kept).
Usage: repair_loop.py <label> <base_url> <model_id> [max_rounds]
"""
from __future__ import annotations
import json, pathlib, sys, urllib.request
import grade_personal as G
import _exec

HERE = pathlib.Path(__file__).resolve().parent
SCEN = {s["id"]: s for s in json.loads((HERE / "scenarios_personal.json").read_text())["scenarios"]}
MAX_ROUNDS = int(sys.argv[4]) if len(sys.argv) > 4 else 3


def chat(base, model, messages, max_tokens):
    body = json.dumps({"model": model, "messages": messages,
                       "max_tokens": max_tokens, "temperature": 0}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/v1/chat/completions",
                                 data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1200) as r:
        d = json.loads(r.read())
    return d["choices"][0]["message"].get("content") or ""


def grade(sid, text):
    """Grade one saved answer with FULL error text for feedback. None = judged."""
    chk = SCEN[sid]["check"]
    if chk == "py":
        err = "no code found"
        for c in G.py_candidates(text):
            ok, err = _exec.run_python(c, G.TESTS[sid])
            if ok:
                return True, ""
        return False, err[-1200:]
    if chk == "rust":
        err = "no code found"
        for c in G.rust_candidates(text, prefer_last=(sid == "rs-04")):
            ok, err = _exec.compile_rust(c)
            if ok:
                return True, ""
        return False, err[:1200]
    return None, ""


def main():
    label, base, model = sys.argv[1], sys.argv[2], sys.argv[3]
    out = HERE / "out" / label
    rep = out / "repair"; rep.mkdir(parents=True, exist_ok=True)
    results = {}
    for sid, s in SCEN.items():
        if s["check"] not in ("py", "rust"):
            continue
        text = (out / f"{sid}.txt").read_text()
        ok, err = grade(sid, text)
        if ok:
            results[sid] = 0
            print(f"  {label} {sid}: first-shot ✅ (0 rounds)", flush=True)
            continue
        budget = max(int(s["max_tokens"] * 1.5), 2000)
        converged = None
        for r in range(1, MAX_ROUNDS + 1):
            msgs = [
                {"role": "user", "content": s["prompt"]},
                {"role": "assistant", "content": text},
                {"role": "user", "content":
                    "Your solution failed automated testing with this error:\n\n```\n"
                    + err + "\n```\n\nFix it. Keep the EXACT required name/signature. "
                    "Return the COMPLETE corrected solution in ONE code block."},
            ]
            try:
                text = chat(base, model, msgs, budget)
            except Exception as exc:  # noqa: BLE001
                err = f"[request error: {exc}]"; break
            (rep / f"{sid}.r{r}.txt").write_text(text)
            ok, err = grade(sid, text)
            if ok:
                converged = r; break
        results[sid] = converged if converged is not None else "DNC"
        tag = f"converged in {converged} round(s) ✅" if converged else f"DID NOT CONVERGE in {MAX_ROUNDS} ❌"
        print(f"  {label} {sid}: first-shot ❌ -> {tag}", flush=True)
    (out / "_repair.json").write_text(json.dumps(results, indent=1))
    fs = sum(1 for v in results.values() if v == 0)
    conv = sum(1 for v in results.values() if isinstance(v, int) and v > 0)
    dnc = sum(1 for v in results.values() if v == "DNC")
    print(f"### {label}: first-shot {fs} | repaired {conv} | stuck {dnc} "
          f"=> {fs + conv}/{len(results)} solved within {MAX_ROUNDS} rounds", flush=True)


if __name__ == "__main__":
    main()

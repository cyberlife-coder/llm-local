#!/usr/bin/env python3
"""Objective compile-check for the Rust eval scenarios.

For each Rust scenario, extract the code from a model's output
(evals/out/<label>/<id>.txt), compile it with `rustc --crate-type lib`
(type-checks + borrow-checks without needing a main), and report pass/fail.

This is the objective half of grading the Rust cases (analogous to grade.py
for math/business). A clean compile does NOT prove correctness — the rubric
still judges logic — but a model whose Rust does not even compile fails the
most basic bar.

Usage:
    python3 evals/rust_check.py <label> [<label> ...]
    python3 evals/rust_check.py glm47-flash supergemma4-26b
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
RUST_IDS = ["code-08", "code-09", "cplx-08", "cplx-09", "debug-06", "debug-07"]


def extract_candidates(text: str, prefer_last: bool = False) -> list[str]:
    """Return candidate Rust sources to try compiling, best-first.

    Models format answers inconsistently: some put imports + impl + a usage
    example in one fence, some split them, and debugging answers often quote
    the BROKEN code then give the FIX in a later block. So we try several
    reasonable reconstructions and accept the scenario if ANY compiles:
      - concatenation of all Rust-looking blocks (imports split out),
      - the single largest block (avoids duplicate-definition when a model
        shows two full versions),
      - the last block (the fix, for debugging).
    """
    fences = re.findall(r"```(?:rust|rs)?\s*\n(.*?)```", text, re.DOTALL)
    if not fences:
        m = re.search(r"```(?:rust|rs)?\s*\n(.*)", text, re.DOTALL)  # unclosed/truncated
        if m:
            fences = [m.group(1)]
    blocks = [b for b in fences if "fn " in b or "impl " in b or "struct " in b] or fences
    if not blocks:
        return [text]
    cands = []
    if prefer_last:
        cands.append(blocks[-1])
    cands.append("\n\n".join(blocks))          # concatenated (imports + impl)
    cands.append(max(blocks, key=len))          # largest single block
    cands.append(blocks[-1])                     # last block
    seen, out = set(), []
    for c in cands:                              # dedupe, preserve order
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def compiles(code: str) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as d:
        src = pathlib.Path(d) / "probe.rs"
        src.write_text(code)
        try:
            p = subprocess.run(
                ["rustc", "--edition", "2021", "--crate-type", "lib",
                 "-o", str(pathlib.Path(d) / "out"), str(src)],
                capture_output=True, text=True, timeout=60,
            )
        except FileNotFoundError:
            sys.exit("rustc not found on PATH (install Rust to run this check).")
        except subprocess.TimeoutExpired:
            return False, "rustc timeout"
        if p.returncode == 0:
            return True, ""
        first = next((ln for ln in p.stderr.splitlines() if ln.startswith("error")), "")
        return False, first.strip()


def main() -> None:
    labels = sys.argv[1:]
    if not labels:
        sys.exit("usage: rust_check.py <label> [<label> ...]")
    for label in labels:
        out = HERE / "out" / label
        print(f"\n## {label}")
        passed = 0
        for rid in RUST_IDS:
            f = out / f"{rid}.txt"
            if not f.exists():
                print(f"  {rid}: (no output)")
                continue
            ok, err = False, ""
            for cand in extract_candidates(f.read_text(), prefer_last=rid.startswith("debug")):
                ok, err = compiles(cand)
                if ok:
                    break
            passed += ok
            print(f"  {rid}: {'COMPILES ✅' if ok else 'FAILS ❌  ' + err}")
        print(f"  -> {passed}/{len(RUST_IDS)} compile")


if __name__ == "__main__":
    main()

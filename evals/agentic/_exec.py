#!/usr/bin/env python3
"""Sandboxed exec helpers shared by the objective graders.

Run model-produced Python against a test harness, and compile model-produced
Rust as a library. Both return (ok, full_error); callers truncate as they like.
"""
from __future__ import annotations
import pathlib, subprocess, sys, tempfile


def run_python(code, test, timeout=30):
    """Append a test harness to `code`, run it in a subprocess. (ok, full_error)."""
    src = code + "\n\n# ===TEST===\n" + test + "\nprint('OK_PERSONAL')\n"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(src); path = f.name
    try:
        p = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "Test timed out (likely a deadlock / infinite loop)."
    finally:
        pathlib.Path(path).unlink(missing_ok=True)
    if p.returncode == 0 and "OK_PERSONAL" in p.stdout:
        return True, ""
    return False, (p.stderr.strip() or p.stdout.strip() or "(no output)")


def compile_rust(code, timeout=60):
    """Compile `code` as a library with rustc (type+borrow check). (ok, full_error)."""
    with tempfile.TemporaryDirectory() as d:
        src = pathlib.Path(d) / "probe.rs"; src.write_text(code)
        try:
            p = subprocess.run(["rustc", "--edition", "2021", "--crate-type", "lib",
                                "-o", str(pathlib.Path(d) / "out"), str(src)],
                               capture_output=True, text=True, timeout=timeout)
        except FileNotFoundError:
            sys.exit("rustc not found on PATH (install Rust to run this check).")
        except subprocess.TimeoutExpired:
            return False, "rustc timeout"
    if p.returncode == 0:
        return True, ""
    return False, p.stderr.strip()

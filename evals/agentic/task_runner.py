#!/usr/bin/env python3
"""Run the 350-word verify (optional) + the Kanban app build on one endpoint.
Saves the extracted HTML to out_kanban/<label>.html and raw answer to <label>.md.
Usage: task_runner.py <label> <base_url> <budget> <do_350:0|1>
"""
from __future__ import annotations
import json, pathlib, re, sys, time, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out_kanban"; OUT.mkdir(exist_ok=True)

TCP = ("Explain in detail how TCP congestion control works. Cover slow start, congestion "
       "avoidance, the AIMD principle, fast retransmit, and fast recovery, and how the "
       "congestion window evolves over time. Write roughly 350 words of clear prose.")

KANBAN = ("Create a COMPLETE, self-contained Kanban board web application in a SINGLE HTML file "
          "(inline <style> + vanilla <script>, no frameworks, no external resources/CDNs). Requirements: "
          "three columns 'To Do', 'In Progress', 'Done'; ADD a new task (title + optional description) to a column; "
          "EDIT a task inline; DELETE a task; DRAG-AND-DROP cards between columns AND reorder within a column using "
          "the native HTML5 Drag and Drop API (dragstart/dragover/drop); PERSIST state to localStorage so it survives "
          "reload; a clean, modern UI. Output ONLY the complete HTML file in ONE code block.")


def call(base, prompt, max_tokens):
    body = json.dumps({"model": "default", "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/v1/messages", data=body,
                                 headers={"Content-Type": "application/json",
                                          "anthropic-version": "2023-06-01", "x-api-key": "local"})
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=1800) as r:
        d = json.loads(r.read())
    dt = time.monotonic() - t0
    blocks = d.get("content") or []
    think = sum(len(b.get("thinking", "")) for b in blocks if b.get("type") == "thinking")
    ans = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    ot = (d.get("usage") or {}).get("output_tokens") or 0
    return dt, ot, think, ans, d.get("stop_reason")


def extract_html(text):
    m = re.findall(r"```(?:html)?\s*\n(.*?)```", text, re.DOTALL)
    cands = [b for b in m if "<html" in b.lower() or "<!doctype" in b.lower()] or m
    if not cands:
        return text  # maybe raw html without fences
    return max(cands, key=len)


def main():
    label, base, budget, do350 = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4] == "1"
    print(f"\n## {label} (budget={budget})", flush=True)
    if do350:
        dt, ot, think, ans, stop = call(base, TCP, budget)
        print(f"  [350w-verify] {dt:.1f}s  {ot} tok  answer_words={len(ans.split())}  "
              f"think={think}c ans={len(ans)}c stop={stop}", flush=True)
    dt, ot, think, ans, stop = call(base, KANBAN, budget)
    html = extract_html(ans)
    (OUT / f"{label}.md").write_text(ans)
    (OUT / f"{label}.html").write_text(html)
    complete = "yes" if "</html>" in html.lower() else "NO(truncated)"
    print(f"  [kanban] {dt:.1f}s  {ot} tok  think={think}c ans={len(ans)}c  "
          f"html={len(html)}c complete={complete} stop={stop}", flush=True)


if __name__ == "__main__":
    main()

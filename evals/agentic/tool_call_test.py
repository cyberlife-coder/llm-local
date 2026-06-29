#!/usr/bin/env python3
"""Tool-calling test on the ANTHROPIC /v1/messages path (the claude-local path).

Sends Anthropic-format requests with `tools` and checks the model emits valid
`tool_use` blocks: right tool name, JSON-parseable input, required args present
with sensible values; multi-turn chaining (tool_result -> final answer); and
abstention (no spurious tool call when none is needed).

Usage: tool_call_test.py <label> <base_url> [id1,id2,...]
Saves raw responses to out/<label>/tools/<id>.json. Stdlib only.
"""
from __future__ import annotations
import json, pathlib, sys, urllib.request

HERE = pathlib.Path(__file__).resolve().parent

WEATHER = {"name": "get_weather", "description": "Get current weather for a city.",
           "input_schema": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}
GETTIME = {"name": "get_time", "description": "Get the current local time for a city or timezone.",
           "input_schema": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}}
STOCK = {"name": "get_stock_price", "description": "Get the latest stock price for a ticker.",
         "input_schema": {"type": "object", "properties": {"ticker": {"type": "string"}}, "required": ["ticker"]}}
CONVERT = {"name": "convert_currency", "description": "Convert an amount between currencies.",
           "input_schema": {"type": "object", "properties": {
               "amount": {"type": "number"}, "from_currency": {"type": "string"}, "to_currency": {"type": "string"}},
               "required": ["amount", "from_currency", "to_currency"]}}
READFILE = {"name": "read_file", "description": "Read a file from disk and return its contents.",
            "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}
SETPRIO = {"name": "set_priority", "description": "Set the priority level of a task.",
           "input_schema": {"type": "object", "properties": {
               "task_id": {"type": "string"}, "level": {"type": "string", "enum": ["low", "medium", "high"]}},
               "required": ["task_id", "level"]}}
WEBSEARCH = {"name": "web_search", "description": "Search the web and return top results.",
             "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}

SCENARIOS = [
    {"id": "tc-01", "tools": [WEATHER], "kind": "tool", "msg": "What's the weather in Paris right now?",
     "want_name": "get_weather", "args": {"city": "paris"}},
    {"id": "tc-02", "tools": [WEATHER, STOCK, GETTIME], "kind": "tool",
     "msg": "What time is it in Tokyo at the moment?", "want_name": "get_time", "args": {"location": "tokyo"}},
    {"id": "tc-03", "tools": [CONVERT], "kind": "tool", "msg": "Convert 250 US dollars into euros.",
     "want_name": "convert_currency", "args": {"amount": "250", "from_currency": "usd|dollar", "to_currency": "eur|euro"}},
    {"id": "tc-04", "tools": [WEATHER], "kind": "no_tool",
     "msg": "In one sentence, define what recursion is in programming. Answer directly."},
    {"id": "tc-05", "tools": [READFILE], "kind": "chain", "msg": "Open config.json and tell me the value of the \"port\" field.",
     "want_name": "read_file", "tool_result": '{"port": 8443, "host": "localhost"}', "final_contains": "8443"},
    {"id": "tc-06", "tools": [WEATHER], "kind": "multi", "msg": "Compare the current weather in Paris and Tokyo.",
     "want_name": "get_weather", "cities": ["paris", "tokyo"]},
    {"id": "tc-07", "tools": [SETPRIO], "kind": "tool", "msg": "Mark task T-42 as high priority.",
     "want_name": "set_priority", "args": {"task_id": "t-42", "level": "high"}},
    {"id": "tc-08", "tools": [WEBSEARCH], "kind": "chain", "msg": "Search for the capital of Australia and tell me what it is.",
     "want_name": "web_search", "tool_result": "Top result: Canberra is the capital city of Australia.",
     "final_contains": "canberra"},
]


def messages(base, tools, msgs, max_tokens=1024):
    body = json.dumps({"model": "default", "max_tokens": max_tokens, "messages": msgs, "tools": tools}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/v1/messages", data=body,
                                 headers={"Content-Type": "application/json", "anthropic-version": "2023-06-01",
                                          "x-api-key": "local"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def tool_uses(resp):
    return [b for b in (resp.get("content") or []) if isinstance(b, dict) and b.get("type") == "tool_use"]


def text_of(resp):
    return " ".join(b.get("text", "") for b in (resp.get("content") or [])
                    if isinstance(b, dict) and b.get("type") == "text")


def check_args(got, want):
    for k, expected in want.items():
        if k not in got:
            return False, f"missing arg '{k}'"
        val = str(got[k]).strip().lower()
        opts = str(expected).lower().split("|")
        if not any(o in val or val in o for o in opts):
            return False, f"arg '{k}'={got[k]!r} !~ {expected!r}"
    return True, ""


def run_one(base, s, out):
    try:
        msgs = [{"role": "user", "content": s["msg"]}]
        resp = messages(base, s["tools"], msgs)
    except Exception as exc:  # noqa: BLE001
        return False, f"request error: {exc}"
    (out / f"{s['id']}.json").write_text(json.dumps(resp, indent=1)[:8000])
    tus = tool_uses(resp)

    if s["kind"] == "no_tool":
        if tus:
            return False, f"spurious tool_use ({tus[0].get('name')}) when none needed"
        return (bool(text_of(resp).strip()), "" if text_of(resp).strip() else "no text answer")

    if not tus:
        return False, "no tool_use emitted (text only) — bridge/model did not call the tool"

    if s["kind"] == "multi":
        cities = [str(tu.get("input", {}).get("city", "")).lower() for tu in tus if tu.get("name") == s["want_name"]]
        hit = [c for c in s["cities"] if any(c in cc for cc in cities)]
        if len(hit) >= 2:
            return True, f"both cities ({len(tus)} call(s))"
        if len(hit) == 1:
            return "PARTIAL", f"only 1 city ({hit}) in {len(tus)} call(s)"
        return False, f"wrong cities: {cities}"

    tu = next((t for t in tus if t.get("name") == s["want_name"]), tus[0])
    if tu.get("name") != s["want_name"]:
        return False, f"wrong tool: {tu.get('name')} (wanted {s['want_name']})"
    if not isinstance(tu.get("input"), dict):
        return False, "input not a dict / not JSON"

    if s["kind"] == "tool":
        ok, why = check_args(tu["input"], s["args"])
        return (ok, why if not ok else f"input={tu['input']}")

    if s["kind"] == "chain":
        # turn 2: feed a synthetic tool_result, expect the final answer to use it
        try:
            msgs2 = [{"role": "user", "content": s["msg"]},
                     {"role": "assistant", "content": resp["content"]},
                     {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tu.get("id", "x"),
                                                    "content": s["tool_result"]}]}]
            resp2 = messages(base, s["tools"], msgs2)
        except Exception as exc:  # noqa: BLE001
            return False, f"turn-2 error: {exc}"
        (out / f"{s['id']}.turn2.json").write_text(json.dumps(resp2, indent=1)[:8000])
        final = text_of(resp2).lower()
        if s["final_contains"].lower() in final:
            return True, f"chained ok (final cites '{s['final_contains']}')"
        return False, f"final answer missing '{s['final_contains']}': {final[:80]!r}"
    return False, "unhandled kind"


def main():
    label, base = sys.argv[1], sys.argv[2]
    ids = sys.argv[3].split(",") if len(sys.argv) > 3 else [s["id"] for s in SCENARIOS]
    out = HERE / "out" / label / "tools"; out.mkdir(parents=True, exist_ok=True)
    print(f"\n## {label}")
    score = 0.0
    for s in SCENARIOS:
        if s["id"] not in ids:
            continue
        ok, why = run_one(base, s, out)
        mark = "PASS ✅" if ok is True else ("PARTIAL ◐" if ok == "PARTIAL" else "FAIL ❌")
        score += 1.0 if ok is True else (0.5 if ok == "PARTIAL" else 0.0)
        print(f"  {s['id']} [{s['kind']:7}] {mark}  {why}", flush=True)
    print(f"### {label} tool-calling: {score}/{len([s for s in SCENARIOS if s['id'] in ids])}", flush=True)


if __name__ == "__main__":
    main()

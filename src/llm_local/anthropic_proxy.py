"""Anthropic-compatible front end for an OpenAI-only backend (mlx_lm.server).

This bundled proxy lets `llm-local claude-local` (which speaks the Anthropic
Messages API) drive a model served by `mlx_lm.server` (which only speaks the
OpenAI Chat Completions API). It also passes OpenAI requests straight through,
so a single public port serves both APIs - mirroring what vllm-mlx provides.

It is intentionally dependency-free (standard library only) and spawns
`mlx_lm.server` as a supervised child process, so the whole thing is one
tracked PID from `llm-local`'s point of view.

Run standalone:
    python -m llm_local.anthropic_proxy --model /path/to/model --port 8006
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


# ---------------------------------------------------------------------------
# Translation helpers (pure functions, unit-tested)
# ---------------------------------------------------------------------------

_FINISH_TO_STOP = {
    "stop": "end_turn",
    "length": "max_tokens",
    "tool_calls": "tool_use",
    "content_filter": "end_turn",
    "function_call": "tool_use",
}


def _text_from_blocks(blocks: Any) -> str:
    if isinstance(blocks, str):
        return blocks
    if not isinstance(blocks, list):
        return ""
    parts = []
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


def _stringify_tool_result(content: Any) -> str:
    """Anthropic tool_result content may be a string or a list of blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return _text_from_blocks(content)
    if content is None:
        return ""
    return json.dumps(content)


def anthropic_to_openai_request(body: dict, model: str) -> dict:
    """Translate an Anthropic /v1/messages body into an OpenAI chat body."""
    messages: list[dict] = []

    system = body.get("system")
    if system:
        messages.append({"role": "system", "content": _text_from_blocks(system)})

    for msg in body.get("messages", []):
        role = msg.get("role", "user")
        content = msg.get("content")

        if isinstance(content, str):
            messages.append({"role": role, "content": content})
            continue

        if not isinstance(content, list):
            continue

        text_parts: list[str] = []
        tool_calls: list[dict] = []
        tool_results: list[dict] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "text":
                text_parts.append(block.get("text", ""))
            elif btype == "tool_use":
                tool_calls.append(
                    {
                        "id": block.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": block.get("name", ""),
                            "arguments": json.dumps(block.get("input", {})),
                        },
                    }
                )
            elif btype == "tool_result":
                tool_results.append(
                    {
                        "role": "tool",
                        "tool_call_id": block.get("tool_use_id", ""),
                        "content": _stringify_tool_result(block.get("content")),
                    }
                )
            # image / other block types are dropped (text-only backend)

        if role == "assistant":
            entry: dict = {"role": "assistant"}
            entry["content"] = "".join(text_parts) or None
            if tool_calls:
                entry["tool_calls"] = tool_calls
            messages.append(entry)
        else:
            # User turn: text first (if any), then each tool result as its own
            # OpenAI `tool` message (the order OpenAI expects).
            if text_parts:
                messages.append({"role": "user", "content": "".join(text_parts)})
            messages.extend(tool_results)

    out: dict = {"model": model, "messages": messages}

    if "max_tokens" in body:
        out["max_tokens"] = body["max_tokens"]
    if "temperature" in body:
        out["temperature"] = body["temperature"]
    if "top_p" in body:
        out["top_p"] = body["top_p"]
    if body.get("stop_sequences"):
        out["stop"] = body["stop_sequences"]
    if body.get("stream"):
        out["stream"] = True

    if body.get("tools"):
        out["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {}) or {},
                },
            }
            for t in body["tools"]
            if isinstance(t, dict)
        ]
        out["tool_choice"] = _tool_choice(body.get("tool_choice"))

    return out


def _tool_choice(choice: Any) -> Any:
    if not isinstance(choice, dict):
        return "auto"
    ctype = choice.get("type")
    if ctype == "any":
        return "required"
    if ctype == "tool" and choice.get("name"):
        return {"type": "function", "function": {"name": choice["name"]}}
    return "auto"


_DUMMY_SIGNATURE = "local"  # local models can't sign thinking blocks


def openai_to_anthropic_response(oai: dict, model: str, expose_reasoning: bool = False) -> dict:
    """Translate a non-streaming OpenAI chat completion into an Anthropic message."""
    choice = (oai.get("choices") or [{}])[0]
    message = choice.get("message") or {}

    content: list[dict] = []
    if expose_reasoning:
        reasoning = message.get("reasoning") or message.get("reasoning_content")
        if reasoning:
            content.append({"type": "thinking", "thinking": reasoning, "signature": _DUMMY_SIGNATURE})
    text = message.get("content")
    if text:
        content.append({"type": "text", "text": text})
    for call in message.get("tool_calls") or []:
        fn = call.get("function") or {}
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except (ValueError, TypeError):
            args = {}
        content.append(
            {
                "type": "tool_use",
                "id": call.get("id", ""),
                "name": fn.get("name", ""),
                "input": args,
            }
        )
    if not content:
        content.append({"type": "text", "text": ""})

    usage = oai.get("usage") or {}
    return {
        "id": oai.get("id", "msg_local"),
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content,
        "stop_reason": _FINISH_TO_STOP.get(choice.get("finish_reason"), "end_turn"),
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        },
    }


def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode("utf-8")


class StreamTranslator:
    """Turns an OpenAI streaming chat completion into Anthropic SSE events.

    Feed raw upstream `data:` payloads (already JSON-decoded) to `feed()`, then
    call `finish()`. Both yield encoded Anthropic SSE byte chunks.
    """

    def __init__(self, model: str, expose_reasoning: bool = False):
        self.model = model
        self.expose_reasoning = expose_reasoning
        self.started = False
        self.next_index = 0
        self.open_index: int | None = None
        self.open_kind: str | None = None  # "thinking" | "text" | "tool"
        self.tool_index_map: dict[int, int] = {}  # openai tool idx -> block idx
        self.stop_reason = "end_turn"
        self.output_tokens = 0

    def _start(self):
        self.started = True
        yield _sse(
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": "msg_local",
                    "type": "message",
                    "role": "assistant",
                    "model": self.model,
                    "content": [],
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {"input_tokens": 0, "output_tokens": 0},
                },
            },
        )

    def _close_open(self):
        if self.open_index is not None:
            if self.open_kind == "thinking":
                yield _sse(
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": self.open_index,
                        "delta": {"type": "signature_delta", "signature": _DUMMY_SIGNATURE},
                    },
                )
            yield _sse(
                "content_block_stop",
                {"type": "content_block_stop", "index": self.open_index},
            )
            self.open_index = None
            self.open_kind = None

    def feed(self, chunk: dict):
        if not self.started:
            yield from self._start()

        choice = (chunk.get("choices") or [{}])[0]
        delta = choice.get("delta") or {}

        if self.expose_reasoning:
            reasoning = delta.get("reasoning") or delta.get("reasoning_content")
            if reasoning:
                if self.open_kind != "thinking":
                    yield from self._close_open()
                    self.open_index = self.next_index
                    self.next_index += 1
                    self.open_kind = "thinking"
                    yield _sse(
                        "content_block_start",
                        {
                            "type": "content_block_start",
                            "index": self.open_index,
                            "content_block": {"type": "thinking", "thinking": ""},
                        },
                    )
                yield _sse(
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": self.open_index,
                        "delta": {"type": "thinking_delta", "thinking": reasoning},
                    },
                )

        text = delta.get("content")
        if text:
            if self.open_kind != "text":
                yield from self._close_open()
                self.open_index = self.next_index
                self.next_index += 1
                self.open_kind = "text"
                yield _sse(
                    "content_block_start",
                    {
                        "type": "content_block_start",
                        "index": self.open_index,
                        "content_block": {"type": "text", "text": ""},
                    },
                )
            yield _sse(
                "content_block_delta",
                {
                    "type": "content_block_delta",
                    "index": self.open_index,
                    "delta": {"type": "text_delta", "text": text},
                },
            )

        for tc in delta.get("tool_calls") or []:
            oai_idx = tc.get("index", 0)
            fn = tc.get("function") or {}
            if oai_idx not in self.tool_index_map:
                yield from self._close_open()
                block_idx = self.next_index
                self.next_index += 1
                self.tool_index_map[oai_idx] = block_idx
                self.open_index = block_idx
                self.open_kind = "tool"
                yield _sse(
                    "content_block_start",
                    {
                        "type": "content_block_start",
                        "index": block_idx,
                        "content_block": {
                            "type": "tool_use",
                            "id": tc.get("id", ""),
                            "name": fn.get("name", ""),
                            "input": {},
                        },
                    },
                )
            frag = fn.get("arguments")
            if frag:
                yield _sse(
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": self.tool_index_map[oai_idx],
                        "delta": {"type": "input_json_delta", "partial_json": frag},
                    },
                )

        if choice.get("finish_reason"):
            self.stop_reason = _FINISH_TO_STOP.get(choice["finish_reason"], "end_turn")

        usage = chunk.get("usage")
        if usage and usage.get("completion_tokens") is not None:
            self.output_tokens = usage["completion_tokens"]

    def finish(self):
        if not self.started:
            yield from self._start()
        yield from self._close_open()
        yield _sse(
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": self.stop_reason, "stop_sequence": None},
                "usage": {"output_tokens": self.output_tokens},
            },
        )
        yield _sse("message_stop", {"type": "message_stop"})


# ---------------------------------------------------------------------------
# HTTP proxy
# ---------------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class ProxyConfig:
    upstream: str = ""
    model: str = ""
    expose_reasoning: bool = False


def _make_handler(cfg: ProxyConfig):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):  # quieter logs
            sys.stderr.write("proxy: " + (args[0] % args[1:]) + "\n")

        def _read_body(self) -> bytes:
            length = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(length) if length else b""

        def _send_json(self, status: int, payload: dict):
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._passthrough(b"")

        def do_POST(self):
            body = self._read_body()
            if self.path.rstrip("/").endswith("/v1/messages"):
                self._handle_messages(body)
            else:
                self._passthrough(body)

        # -- Anthropic bridge -------------------------------------------------
        def _handle_messages(self, body: bytes):
            try:
                anthropic_req = json.loads(body or b"{}")
            except ValueError:
                self._send_json(400, {"type": "error", "error": {"message": "bad json"}})
                return
            stream = bool(anthropic_req.get("stream"))
            oai_req = anthropic_to_openai_request(anthropic_req, cfg.model)
            url = cfg.upstream + "/v1/chat/completions"
            data = json.dumps(oai_req).encode("utf-8")
            req = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"}
            )
            try:
                resp = urllib.request.urlopen(req)
            except urllib.error.HTTPError as exc:
                self._send_json(exc.code, {"type": "error", "error": {"message": exc.read().decode("utf-8", "replace")}})
                return
            except urllib.error.URLError as exc:
                self._send_json(502, {"type": "error", "error": {"message": str(exc)}})
                return

            if not stream:
                oai = json.loads(resp.read())
                self._send_json(
                    200, openai_to_anthropic_response(oai, cfg.model, cfg.expose_reasoning)
                )
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            translator = StreamTranslator(cfg.model, cfg.expose_reasoning)
            try:
                for raw in resp:
                    line = raw.decode("utf-8", "replace").strip()
                    if not line.startswith("data:"):
                        continue
                    payload = line[len("data:"):].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except ValueError:
                        continue
                    for out in translator.feed(chunk):
                        self.wfile.write(out)
                    self.wfile.flush()
                for out in translator.finish():
                    self.wfile.write(out)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

        # -- transparent OpenAI passthrough ----------------------------------
        def _passthrough(self, body: bytes):
            # mlx_lm.server selects the model by the request's `model` field, so
            # force it to the single loaded model (clients may send anything).
            if body:
                try:
                    parsed = json.loads(body)
                    if isinstance(parsed, dict) and "model" in parsed:
                        parsed["model"] = cfg.model
                        body = json.dumps(parsed).encode("utf-8")
                except ValueError:
                    pass
            url = cfg.upstream + self.path
            method = self.command
            headers = {
                k: v
                for k, v in self.headers.items()
                if k.lower() in ("content-type", "accept")
            }
            req = urllib.request.Request(url, data=body or None, headers=headers, method=method)
            try:
                resp = urllib.request.urlopen(req)
            except urllib.error.HTTPError as exc:
                payload = exc.read()
                self.send_response(exc.code)
                self.send_header("Content-Type", exc.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            except urllib.error.URLError as exc:
                self._send_json(502, {"error": {"message": str(exc)}})
                return
            ctype = resp.headers.get("Content-Type", "application/json")
            if "text/event-stream" in ctype:
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                try:
                    for raw in resp:
                        self.wfile.write(raw)
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
            else:
                payload = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

    return Handler


def _wait_ready(upstream: str, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(upstream + "/v1/models", timeout=2) as r:
                if r.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(1.0)
    return False


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="llm_local.anthropic_proxy")
    parser.add_argument("--model", required=True, help="Path or HF id passed to mlx_lm.server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True, help="Public port (Anthropic + OpenAI)")
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument(
        "--expose-reasoning",
        action="store_true",
        help="Surface the model's reasoning channel as Anthropic `thinking` blocks.",
    )
    parser.add_argument("--ready-timeout", type=float, default=600.0)
    parser.add_argument(
        "--mlx-cmd",
        default=os.environ.get("LLM_LOCAL_MLX_LM", "uvx --from mlx-lm mlx_lm.server"),
        help="Command that launches an OpenAI-compatible mlx_lm server.",
    )
    # Unknown flags (e.g. --chat-template-args, --temp) are forwarded verbatim
    # to the mlx_lm child, so profiles can pass any mlx_lm.server option.
    args, extra = parser.parse_known_args(argv)

    upstream_port = _free_port()
    upstream = f"http://127.0.0.1:{upstream_port}"

    child_cmd = shlex.split(args.mlx_cmd) + [
        "--model", args.model,
        "--host", "127.0.0.1",
        "--port", str(upstream_port),
    ]
    if args.max_tokens is not None:
        child_cmd += ["--max-tokens", str(args.max_tokens)]
    child_cmd += extra

    print(f"proxy: starting mlx_lm child: {' '.join(child_cmd)}", flush=True)
    child = subprocess.Popen(child_cmd, stdout=sys.stdout, stderr=subprocess.STDOUT)

    def shutdown(*_):
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                child.kill()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    print(f"proxy: waiting for mlx_lm on {upstream} ...", flush=True)
    if not _wait_ready(upstream, args.ready_timeout):
        print("proxy: upstream mlx_lm failed to become ready", file=sys.stderr, flush=True)
        shutdown()

    cfg = ProxyConfig()
    cfg.upstream = upstream
    cfg.model = args.model
    cfg.expose_reasoning = args.expose_reasoning

    server = ThreadingHTTPServer((args.host, args.port), _make_handler(cfg))
    print(
        f"proxy: listening on http://{args.host}:{args.port} "
        f"(Anthropic /v1/messages + OpenAI passthrough -> {upstream})",
        flush=True,
    )
    try:
        server.serve_forever()
    finally:
        shutdown()


if __name__ == "__main__":
    main()

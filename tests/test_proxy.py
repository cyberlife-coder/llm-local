from __future__ import annotations

import json

from llm_local.anthropic_proxy import (
    StreamTranslator,
    anthropic_to_openai_request,
    openai_to_anthropic_response,
)


def test_request_system_and_text():
    body = {
        "system": "You are helpful.",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 100,
        "temperature": 0.5,
    }
    out = anthropic_to_openai_request(body, "default")
    assert out["model"] == "default"
    assert out["messages"][0] == {"role": "system", "content": "You are helpful."}
    assert out["messages"][1] == {"role": "user", "content": "hi"}
    assert out["max_tokens"] == 100
    assert out["temperature"] == 0.5


def test_request_tool_use_and_result_roundtrip():
    body = {
        "messages": [
            {"role": "user", "content": "weather?"},
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "calling"},
                    {"type": "tool_use", "id": "t1", "name": "get_weather", "input": {"city": "Paris"}},
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "t1", "content": "sunny"},
                ],
            },
        ],
        "tools": [
            {"name": "get_weather", "description": "w", "input_schema": {"type": "object"}},
        ],
    }
    out = anthropic_to_openai_request(body, "default")
    # assistant message carries an OpenAI tool_call with JSON-encoded arguments
    assistant = out["messages"][1]
    assert assistant["role"] == "assistant"
    assert assistant["content"] == "calling"
    call = assistant["tool_calls"][0]
    assert call["id"] == "t1"
    assert call["function"]["name"] == "get_weather"
    assert json.loads(call["function"]["arguments"]) == {"city": "Paris"}
    # tool_result becomes an OpenAI tool message
    tool_msg = out["messages"][2]
    assert tool_msg == {"role": "tool", "tool_call_id": "t1", "content": "sunny"}
    # tools mapping (input_schema -> parameters)
    assert out["tools"][0]["function"]["name"] == "get_weather"
    assert out["tools"][0]["function"]["parameters"] == {"type": "object"}


def test_response_text_and_stop_reason():
    oai = {
        "id": "cmpl-1",
        "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "hello"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2},
    }
    out = openai_to_anthropic_response(oai, "default")
    assert out["type"] == "message"
    assert out["content"] == [{"type": "text", "text": "hello"}]
    assert out["stop_reason"] == "end_turn"
    assert out["usage"] == {"input_tokens": 5, "output_tokens": 2}


def test_response_tool_call_maps_to_tool_use():
    oai = {
        "id": "cmpl-2",
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"id": "c1", "function": {"name": "f", "arguments": '{"a": 1}'}}
                    ],
                },
            }
        ],
    }
    out = openai_to_anthropic_response(oai, "default")
    assert out["stop_reason"] == "tool_use"
    block = out["content"][0]
    assert block["type"] == "tool_use"
    assert block["id"] == "c1"
    assert block["name"] == "f"
    assert block["input"] == {"a": 1}


def test_reasoning_dropped_by_default():
    oai = {
        "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "reasoning": "hmm", "content": "answer"}}],
    }
    out = openai_to_anthropic_response(oai, "default")
    assert [b["type"] for b in out["content"]] == ["text"]


def test_reasoning_exposed_as_thinking_block():
    oai = {
        "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "reasoning": "hmm", "content": "answer"}}],
    }
    out = openai_to_anthropic_response(oai, "default", expose_reasoning=True)
    assert [b["type"] for b in out["content"]] == ["thinking", "text"]
    assert out["content"][0]["thinking"] == "hmm"
    assert "signature" in out["content"][0]


def test_stream_thinking_then_text():
    t = StreamTranslator("default", expose_reasoning=True)
    events = b""
    for chunk in [
        {"choices": [{"delta": {"reasoning": "let me think"}}]},
        {"choices": [{"delta": {"content": "answer"}}]},
        {"choices": [{"delta": {}, "finish_reason": "stop"}]},
    ]:
        for out in t.feed(chunk):
            events += out
    for out in t.finish():
        events += out
    text = events.decode()
    assert "thinking_delta" in text
    assert "signature_delta" in text  # thinking block is closed with a signature
    assert "text_delta" in text


def test_stream_translator_text_sequence():
    t = StreamTranslator("default")
    events = b""
    for chunk in [
        {"choices": [{"delta": {"content": "Hel"}}]},
        {"choices": [{"delta": {"content": "lo"}}]},
        {"choices": [{"delta": {}, "finish_reason": "stop"}]},
    ]:
        for out in t.feed(chunk):
            events += out
    for out in t.finish():
        events += out
    text = events.decode()
    assert "event: message_start" in text
    assert "content_block_start" in text
    assert "text_delta" in text
    assert "event: message_delta" in text
    assert "event: message_stop" in text

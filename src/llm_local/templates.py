from __future__ import annotations


DEFAULT_MODEL_SOURCE = "mlx-community/Qwen3.6-35B-A3B-4bit"


def agent_args(
    *,
    context_tokens: int,
    max_tokens: int,
    max_request_tokens: int,
    timeout: int | None = None,
    paged_cache: bool = False,
) -> list[str]:
    args = [
        "--served-model-name",
        "default",
        "--reasoning-parser",
        "qwen3",
        "--enable-auto-tool-choice",
        "--tool-call-parser",
        "auto",
        "--kv-cache-quantization",
        "--kv-cache-quantization-bits",
        "8",
    ]
    if paged_cache:
        args.extend(["--use-paged-cache", "--chunked-prefill-tokens", "8192"])
    args.extend(
        [
            "--max-kv-size",
            str(context_tokens),
            "--max-request-tokens",
            str(max_request_tokens),
            "--max-tokens",
            str(max_tokens),
        ]
    )
    if timeout is not None:
        args.extend(["--timeout", str(timeout)])
    args.extend(["--default-chat-template-kwargs", '{"enable_thinking": false}'])
    return args


def default_config(models_dir: str) -> dict:
    qwen_local = f"{models_dir}/qwen36-a3b"
    return {
        "default_model": "qwen36-a3b-64k",
        "models": {
            "qwen36-a3b": {
                "display_name": "Qwen3.6 35B A3B 4-bit",
                "source": DEFAULT_MODEL_SOURCE,
                "model": qwen_local,
                "host": "127.0.0.1",
                "port": 8000,
                "args": [
                    "--served-model-name",
                    "default",
                    "--reasoning-parser",
                    "qwen3",
                    "--enable-auto-tool-choice",
                    "--tool-call-parser",
                    "auto",
                    "--max-kv-size",
                    "32768",
                    "--max-request-tokens",
                    "8192",
                    "--max-tokens",
                    "8192",
                    "--default-chat-template-kwargs",
                    '{"enable_thinking": false}',
                ],
            },
            "qwen36-a3b-64k": {
                "display_name": "Qwen3.6 35B A3B 4-bit - 64k Claude-like agent profile",
                "source": DEFAULT_MODEL_SOURCE,
                "model": qwen_local,
                "host": "127.0.0.1",
                "port": 8003,
                "args": agent_args(
                    context_tokens=65536,
                    max_tokens=16384,
                    max_request_tokens=16384,
                    timeout=900,
                ),
            },
            "qwen36-a3b-128k": {
                "display_name": "Qwen3.6 35B A3B 4-bit - 128k extended agent profile",
                "source": DEFAULT_MODEL_SOURCE,
                "model": qwen_local,
                "host": "127.0.0.1",
                "port": 8002,
                "args": agent_args(
                    context_tokens=131072,
                    max_tokens=16384,
                    max_request_tokens=32768,
                    timeout=1200,
                ),
            },
            "qwen36-a3b-262k": {
                "display_name": "Qwen3.6 35B A3B 4-bit - 262k long-context profile",
                "source": DEFAULT_MODEL_SOURCE,
                "model": qwen_local,
                "host": "127.0.0.1",
                "port": 8004,
                "args": agent_args(
                    context_tokens=262144,
                    max_tokens=32768,
                    max_request_tokens=65536,
                    timeout=1800,
                    paged_cache=True,
                ),
            },
        },
    }


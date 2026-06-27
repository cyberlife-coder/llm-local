from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from . import __version__
from .config import (
    ensure_layout,
    is_downloaded,
    load_config,
    local_model_dir,
    model_config,
    model_local_path,
    read_manifest,
    save_config,
    source_for,
)
from .paths import Paths, resolve_paths
from .process import (
    active_state,
    current_pid,
    port_is_open,
    run_vllm_mlx,
    start_server,
    stop_server,
)
from .templates import DEFAULT_MODEL_SOURCE, agent_args, mlx_lm_args


def default_args() -> list[str]:
    return [
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
    ]


def configured_paths(args: argparse.Namespace | None = None) -> Paths:
    paths = resolve_paths()
    ensure_layout(paths)
    return paths


def cmd_help(_: argparse.Namespace) -> None:
    paths = configured_paths()
    config = load_config(paths)
    default = config.get("default_model", "(none)")
    pid = current_pid(paths)
    if pid and paths.active_path.exists():
        active = active_state(paths)
        status = f"running: {active.get('name', 'unknown')} on http://{active.get('host', '127.0.0.1')}:{active.get('port', 8000)}"
    elif pid:
        status = f"running: PID {pid}"
    else:
        status = "stopped"

    print(
        f"""llm-local {__version__} - local vllm-mlx helper

Install:
  home:     {paths.home}
  config:   {paths.config_path}
  models:   {paths.models_dir}
  default:  {default}
  server:   {status}

Daily flow:
  llm-local doctor                      Check runtime, config, ports, and server state
  llm-local list                        Show configured model profiles
  llm-local cache                       Show models already stored locally
  llm-local serve                       Start the default model profile
  llm-local serve qwen36-a3b-64k        Start the Claude-like agent profile
  llm-local serve qwen36-a3b-128k       Start the extended agent profile
  llm-local serve qwen36-a3b-262k       Start the long-context profile
  llm-local status                      Show server URL, PID, and log path
  llm-local logs                        Show recent logs for the default model
  llm-local stop                        Stop the running local server

Model management:
  llm-local inspect qwen36-a3b
  llm-local pull qwen36-a3b
  llm-local add my-model mlx-community/Some-Model-4bit --port 8005 --local --pull

Connect agents:
  eval "$(llm-local env-openai)"         For OpenAI-compatible clients
  llm-local env-anthropic               Print Anthropic-compatible env vars
  llm-local claude-local                Launch Claude Code against the local server only

Environment:
  LLM_LOCAL_HOME                        Override the runtime home directory
  LLM_LOCAL_VLLM_MLX                    Override the vllm-mlx executable path

Notes:
  The default bind host is 127.0.0.1. Be deliberate before exposing 0.0.0.0.
  Normal 'claude' still uses Anthropic. Only 'llm-local claude-local' points Claude Code at localhost.
  Use 'llm-local <command> --help' for command-specific options.
"""
    )


def cmd_init(_: argparse.Namespace) -> None:
    paths = configured_paths()
    print(f"Initialized llm-local home: {paths.home}")
    print(f"Config: {paths.config_path}")
    print(f"Models: {paths.models_dir}")


def cmd_doctor(_: argparse.Namespace) -> None:
    paths = configured_paths()
    config = load_config(paths)
    print("llm-local doctor")
    print(f"  home: {paths.home}")
    print(f"  config: {paths.config_path} ({'ok' if paths.config_path.exists() else 'missing'})")
    print(f"  models dir: {paths.models_dir}")
    print(f"  vllm-mlx: {paths.vllm_mlx}")
    if shutil.which(str(paths.vllm_mlx)) or Path(str(paths.vllm_mlx)).exists():
        print("  runtime: ok")
    else:
        print("  runtime: not found (install vllm-mlx or set LLM_LOCAL_VLLM_MLX)")

    models = config.get("models", {})
    if any(m.get("backend") == "mlx_lm" for m in models.values()):
        mlx_cmd = os.environ.get("LLM_LOCAL_MLX_LM", "uvx --from mlx-lm mlx_lm.server")
        launcher = mlx_cmd.split()[0]
        ok = shutil.which(launcher) is not None
        print(f"  mlx_lm launcher: {mlx_cmd} ({'ok' if ok else 'not found'})")

    pid = current_pid(paths)
    print(f"  server: {'running PID ' + str(pid) if pid else 'stopped'}")
    for name, model in models.items():
        host = str(model.get("host", "127.0.0.1"))
        port = int(model.get("port", 8000))
        backend = model.get("backend", "vllm_mlx")
        state = "downloaded" if is_downloaded(paths, name, model) else "remote"
        port_state = "listening" if port_is_open(host, port) else "free"
        print(f"  {name}: {backend}, {state}, {host}:{port} {port_state}")


def cmd_list(_: argparse.Namespace) -> None:
    paths = configured_paths()
    config = load_config(paths)
    default = config.get("default_model")
    for name, model in config.get("models", {}).items():
        marker = "*" if name == default else " "
        downloaded = "downloaded" if is_downloaded(paths, name, model) else "remote"
        print(f"{marker} {name}: {model.get('display_name', model['model'])}")
        print(f"    model: {model['model']}")
        if model.get("source"):
            print(f"    source: {model['source']}")
        print(f"    backend: {model.get('backend', 'vllm_mlx')}")
        print(f"    status: {downloaded}")
        print(f"    url:   http://{model.get('host', '127.0.0.1')}:{model.get('port', 8000)}")


def cmd_profiles(_: argparse.Namespace) -> None:
    paths = configured_paths()
    config = load_config(paths)
    for name, model in config.get("models", {}).items():
        args = model.get("args", [])
        backend = model.get("backend", "vllm_mlx")
        port = model.get("port", 8000)
        if backend == "mlx_lm":
            output = args[args.index("--max-tokens") + 1] if "--max-tokens" in args else "default"
            print(f"{name}: backend=mlx_lm, output={output}, port={port}")
            continue
        if "--max-kv-size" not in args:
            continue
        context = args[args.index("--max-kv-size") + 1]
        output = args[args.index("--max-tokens") + 1] if "--max-tokens" in args else "default"
        print(f"{name}: context={context}, output={output}, port={port}")


def cmd_cache(_: argparse.Namespace) -> None:
    paths = configured_paths()
    found = False
    for manifest in sorted(paths.models_dir.glob("*/vllm_mlx_model_manifest.json")):
        found = True
        data = read_manifest(manifest.parent) or {}
        inspection = data.get("inspection", {})
        size = inspection.get("total_size_gb")
        size_text = f"{size} GB" if size is not None else "size unknown"
        print(f"{manifest.parent.name}: {data.get('model_id', manifest.parent)}")
        print(f"    path: {manifest.parent}")
        print(f"    size: {size_text}")
    if not found:
        print(f"No downloaded vllm-mlx models found in {paths.models_dir}")


def cmd_inspect(args: argparse.Namespace) -> None:
    paths = configured_paths()
    target = args.target
    config = load_config(paths)
    if target in config.get("models", {}):
        _, model = model_config(paths, target)
        target = str(model_local_path(paths, target, model) or source_for(model))
    raise SystemExit(run_vllm_mlx(paths, ["model", "inspect", target]))


def cmd_pull(args: argparse.Namespace) -> None:
    paths = configured_paths()
    name, model = model_config(paths, args.model)
    target = Path(args.target_dir).expanduser() if args.target_dir else local_model_dir(paths, name)
    source = args.source or source_for(model)
    target.parent.mkdir(parents=True, exist_ok=True)

    rc = run_vllm_mlx(paths, ["model", "acquire", source, "--target-dir", str(target)])
    if rc != 0:
        raise SystemExit(rc)

    config = load_config(paths)
    config["models"][name]["source"] = source
    config["models"][name]["model"] = str(target)
    save_config(paths, config)
    print(f"Updated {paths.config_path}: {name} now serves from {target}")


def cmd_add(args: argparse.Namespace) -> None:
    paths = configured_paths()
    config = load_config(paths)
    models = config.setdefault("models", {})
    if args.name in models and not args.replace:
        raise SystemExit(f"Model '{args.name}' already exists. Use --replace to overwrite it.")

    backend = getattr(args, "backend", "vllm_mlx")
    profile_args = mlx_lm_args(max_tokens=32768) if backend == "mlx_lm" else default_args()
    models[args.name] = {
        "display_name": args.display_name or args.name,
        "source": args.source,
        "model": str(local_model_dir(paths, args.name)) if args.local else args.source,
        "host": args.host,
        "port": args.port,
        "backend": backend,
        "args": profile_args,
    }
    if args.default:
        config["default_model"] = args.name
    save_config(paths, config)
    print(f"Added {args.name} to {paths.config_path}")
    if args.pull:
        pull_args = argparse.Namespace(model=args.name, source=args.source, target_dir=None)
        cmd_pull(pull_args)


def cmd_serve(args: argparse.Namespace) -> None:
    paths = configured_paths()
    pid = current_pid(paths)
    if pid:
        raise SystemExit(f"Server already running with PID {pid}. Use 'llm-local status' or 'llm-local stop'.")

    name, model = model_config(paths, args.model)
    if args.pull and not is_downloaded(paths, name, model):
        cmd_pull(argparse.Namespace(model=name, source=None, target_dir=None))
        name, model = model_config(paths, name)

    host = str(model.get("host", "127.0.0.1"))
    port = int(model.get("port", 8000))
    if port_is_open(host, port):
        raise SystemExit(f"Port already in use: {host}:{port}")
    if host == "0.0.0.0" and not args.allow_network:
        raise SystemExit("Refusing to bind 0.0.0.0 without --allow-network.")

    pid = start_server(paths, name, model)
    print(f"Started {name} with PID {pid}")
    print(f"Log: {paths.log_dir / f'{name}.log'}")
    print(f"OpenAI base URL: http://{host}:{port}/v1")
    print(f"Anthropic base URL: http://{host}:{port}")


def cmd_stop(_: argparse.Namespace) -> None:
    paths = configured_paths()
    pid = stop_server(paths)
    print(f"Stopped PID {pid}" if pid else "No running llm-local server found.")


def cmd_restart(args: argparse.Namespace) -> None:
    paths = configured_paths()
    stop_server(paths)
    cmd_serve(args)


def cmd_status(_: argparse.Namespace) -> None:
    paths = configured_paths()
    pid = current_pid(paths)
    if not pid:
        print("Server: stopped")
        return
    active = active_state(paths)
    host = active.get("host", "127.0.0.1")
    port = int(active.get("port", 8000))
    health = "listening" if port_is_open(host, port) else "starting"
    print(f"Server: {health}")
    print(f"PID: {pid}")
    print(f"Model: {active.get('name', 'unknown')} ({active.get('model', 'unknown')})")
    print(f"OpenAI: http://{host}:{port}/v1")
    print(f"Anthropic: http://{host}:{port}")
    print(f"Log: {active.get('log', str(paths.log_dir))}")


def cmd_logs(args: argparse.Namespace) -> None:
    paths = configured_paths()
    name, _ = model_config(paths, args.model)
    log_path = paths.log_dir / f"{name}.log"
    if not log_path.exists():
        raise SystemExit(f"No log yet for {name}: {log_path}")
    cmd = ["tail", "-n", str(args.lines)]
    if args.follow:
        cmd.append("-f")
    cmd.append(str(log_path))
    subprocess.run(cmd, check=False)


def active_endpoint(paths: Paths) -> tuple[str, int]:
    active = active_state(paths)
    if active:
        return active.get("host", "127.0.0.1"), int(active.get("port", 8000))
    _, model = model_config(paths, None)
    return model.get("host", "127.0.0.1"), int(model.get("port", 8000))


def active_model(paths: Paths) -> tuple[str, dict]:
    """Resolve the running profile if any, else the default profile."""
    active = active_state(paths)
    if active.get("name"):
        try:
            return model_config(paths, active["name"])
        except SystemExit:
            pass
    return model_config(paths, None)


def arg_value(args: list, flag: str, default: str) -> str:
    if flag in args:
        index = args.index(flag)
        if index + 1 < len(args):
            return str(args[index + 1])
    return default


def local_launch_env(paths: Paths) -> tuple[dict, str, str]:
    """Build an isolated env that points Claude Code at the local server only.

    Returns (env, base_url, served_model). Side effect: writes an isolated
    settings.json under CLAUDE_CONFIG_DIR so the claude.ai login is never
    touched and no API-key approval prompt appears.
    """
    _, model = active_model(paths)
    host = str(model.get("host", "127.0.0.1"))
    port = int(model.get("port", 8000))
    model_args = list(model.get("args", []))
    served = arg_value(model_args, "--served-model-name", "default")
    base_url = f"http://{host}:{port}"

    config_dir = paths.home / "claude-local"
    config_dir.mkdir(parents=True, exist_ok=True)
    settings_path = config_dir / "settings.json"
    settings: dict = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except json.JSONDecodeError:
            settings = {}
    # apiKeyHelper supplies the (server-ignored) key and skips the approval prompt.
    settings.setdefault("apiKeyHelper", "echo not-needed")
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")

    env = os.environ.copy()
    # Drop any inherited credentials so apiKeyHelper wins and OAuth stays unused.
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    env["CLAUDE_CONFIG_DIR"] = str(config_dir)
    env["ANTHROPIC_BASE_URL"] = base_url
    env["ANTHROPIC_MODEL"] = served
    env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = served
    env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = served
    env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = served
    env["ANTHROPIC_SMALL_FAST_MODEL"] = served
    # No CLAUDE_CODE_MAX_OUTPUT_TOKENS override: Claude Code uses its own token
    # defaults, same as a normal session. The served vllm profile must allow them.
    return env, base_url, served


def cmd_env_openai(_: argparse.Namespace) -> None:
    paths = configured_paths()
    host, port = active_endpoint(paths)
    print(f"export OPENAI_BASE_URL=http://{host}:{port}/v1")
    print("export OPENAI_API_KEY=not-needed")


def cmd_env_anthropic(_: argparse.Namespace) -> None:
    paths = configured_paths()
    host, port = active_endpoint(paths)
    print(f"export ANTHROPIC_BASE_URL=http://{host}:{port}")
    print("export ANTHROPIC_API_KEY=not-needed")


def cmd_claude_local(args: argparse.Namespace) -> None:
    paths = configured_paths()
    if shutil.which("claude") is None:
        raise SystemExit("Claude Code CLI 'claude' not found on PATH.")
    env, base_url, served = local_launch_env(paths)
    host, port = active_endpoint(paths)
    if not port_is_open(host, port):
        print(
            f"Warning: no server listening on {host}:{port}. "
            f"Start one with 'llm-local serve' first.",
            file=sys.stderr,
        )
    print(
        f"Launching Claude Code against {base_url} (model '{served}', "
        f"isolated profile {env['CLAUDE_CONFIG_DIR']}; your claude.ai login is untouched).",
        file=sys.stderr,
    )
    passthrough = args.claude_args[1:] if args.claude_args[:1] == ["--"] else args.claude_args
    os.execvpe("claude", ["claude", *passthrough], env)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="llm-local",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Manage local vllm-mlx models and OpenAI/Anthropic-compatible endpoints.",
        epilog=textwrap.dedent(
            """\
            Common commands:
              llm-local                  Show the practical guide
              llm-local init             Create config and runtime directories
              llm-local doctor           Check runtime and configured profiles
              llm-local list             Show configured models and download status
              llm-local serve            Start the default profile
              llm-local stop             Stop the running server
              llm-local status           Show server URL, PID, and log path

            Agent profiles:
              llm-local serve qwen36-a3b-64k
              llm-local serve qwen36-a3b-128k
              llm-local serve qwen36-a3b-262k

            Connect clients:
              eval "$(llm-local env-openai)"
              llm-local claude-local

            Use 'llm-local <command> --help' for command-specific options.
            """
        ),
    )
    parser.add_argument("--version", action="version", version=f"llm-local {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="command")

    sub.add_parser("help", help="Show the practical llm-local guide.").set_defaults(func=cmd_help)
    sub.add_parser("init", help="Create runtime directories and default config.").set_defaults(func=cmd_init)
    sub.add_parser("doctor", help="Check runtime, config, ports, and server state.").set_defaults(func=cmd_doctor)
    sub.add_parser("list", help="Show configured models and download status.").set_defaults(func=cmd_list)
    sub.add_parser("profiles", help="Show profile context/output limits.").set_defaults(func=cmd_profiles)
    sub.add_parser("cache", help="Show models stored locally.").set_defaults(func=cmd_cache)
    sub.add_parser("downloaded", help="Alias for cache.").set_defaults(func=cmd_cache)

    serve = sub.add_parser("serve", help="Start a local vllm-mlx server.")
    serve.add_argument("model", nargs="?")
    serve.add_argument("--pull", "--download", dest="pull", action="store_true", help="Download the configured model first if needed.")
    serve.add_argument("--allow-network", action="store_true", help="Allow serving on 0.0.0.0 if the profile requests it.")
    serve.set_defaults(func=cmd_serve)

    restart = sub.add_parser("restart", help="Stop and start a local vllm-mlx server.")
    restart.add_argument("model", nargs="?")
    restart.add_argument("--pull", "--download", dest="pull", action="store_true")
    restart.add_argument("--allow-network", action="store_true")
    restart.set_defaults(func=cmd_restart)

    inspect = sub.add_parser("inspect", help="Inspect a configured, local, or Hugging Face model.")
    inspect.add_argument("target")
    inspect.set_defaults(func=cmd_inspect)

    pull = sub.add_parser("pull", help="Download a configured model locally.")
    pull.add_argument("model")
    pull.add_argument("--source")
    pull.add_argument("--target-dir")
    pull.set_defaults(func=cmd_pull)

    download = sub.add_parser("download", help="Alias for pull.")
    download.add_argument("model")
    download.add_argument("--source")
    download.add_argument("--target-dir")
    download.set_defaults(func=cmd_pull)

    add = sub.add_parser("add", help="Add a model profile to models.json.")
    add.add_argument("name")
    add.add_argument("source", nargs="?", default=DEFAULT_MODEL_SOURCE)
    add.add_argument("--display-name")
    add.add_argument("--backend", choices=["vllm_mlx", "mlx_lm"], default="vllm_mlx",
                     help="Serving engine: vllm-mlx (default) or mlx_lm via the Anthropic proxy.")
    add.add_argument("--host", default="127.0.0.1")
    add.add_argument("--port", type=int, default=8005)
    add.add_argument("--local", action="store_true", help="Serve from the standard local models directory after pull.")
    add.add_argument("--pull", "--download", dest="pull", action="store_true", help="Download immediately after adding.")
    add.add_argument("--default", action="store_true", help="Make this the default model.")
    add.add_argument("--replace", action="store_true", help="Overwrite an existing entry.")
    add.set_defaults(func=cmd_add)

    sub.add_parser("stop", help="Stop the running local server.").set_defaults(func=cmd_stop)
    sub.add_parser("status", help="Show server status and endpoints.").set_defaults(func=cmd_status)

    logs = sub.add_parser("logs", help="Show server logs.")
    logs.add_argument("model", nargs="?")
    logs.add_argument("-n", "--lines", type=int, default=80)
    logs.add_argument("-f", "--follow", action="store_true")
    logs.set_defaults(func=cmd_logs)

    sub.add_parser("env-openai", help="Print OpenAI-compatible environment variables.").set_defaults(func=cmd_env_openai)
    sub.add_parser("env-anthropic", help="Print Anthropic-compatible environment variables.").set_defaults(func=cmd_env_anthropic)

    claude = sub.add_parser("claude-local", help="Launch Claude Code against the local server only.")
    claude.add_argument("claude_args", nargs=argparse.REMAINDER)
    claude.set_defaults(func=cmd_claude_local)
    return parser


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    if not argv:
        cmd_help(argparse.Namespace())
        return
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        cmd_help(argparse.Namespace())
        return
    args.func(args)


if __name__ == "__main__":
    main()


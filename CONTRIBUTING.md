# Contributing

Thanks for helping improve `llm-local`.

## Local setup

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[test]"
pytest
```

## Design principles

- Keep the CLI thin and inspectable.
- Prefer explicit config over hidden global shell changes.
- Never expose a server on `0.0.0.0` without an explicit user opt-in.
- Keep model downloads and real inference out of unit tests.
- Treat long context as a profile choice, not the default answer to every task.

## Pull requests

Please include:

- A short explanation of the user problem.
- Tests for config/CLI behavior when possible.
- Notes for any behavior that starts processes, changes ports, or touches model cache.


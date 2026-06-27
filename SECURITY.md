# Security

`llm-local` starts local HTTP servers for model inference. Treat those servers
as sensitive, especially when agents can call tools or inspect local files.

## Defaults

- Profiles bind to `127.0.0.1` by default.
- The CLI refuses profiles that bind to `0.0.0.0` unless `--allow-network` is passed.
- No global shell configuration is modified.
- `claude` continues to use Anthropic unless you explicitly run `llm-local claude-local`.

## Recommendations

- Keep local servers bound to `127.0.0.1` unless you understand the network exposure.
- Add vLLM API authentication before exposing a server beyond localhost.
- Avoid committing runtime files such as `models/`, `logs/`, `state/`, `.venv/`, or `models.json`.
- Review model licenses and acceptable-use terms before redistributing configs or artifacts.

## Reporting

If this project is published on GitHub, use private vulnerability reporting if
enabled, or contact the maintainer directly.


# SafeClaw

SafeClaw is a compact, security-first automation agent designed for small servers and Raspberry Pi. It provides a safe CLI execution layer for command and file operations with explicit policy controls.

## Why this exists

- safer-by-default local automation
- low resource usage
- simple markdown-driven agent context (`AGENTS.md`, `SOUL.md`, `TOOLS.md`, etc.)
- optional queue mode and LLM adapters (planned/extendable)

No remote execution is required for the core runtime.

## Quick start

```bash
python -m pip install -e .
```

1. Initialize a starter config:
```bash
python -m saferclaw init-config --path saferclaw.config.json
```

2. Run a command safely:
```bash
python -m saferclaw run "ls -la" --yes --config saferclaw.config.json
```

3. Or execute a plan file:
```bash
python -m saferclaw run-plan examples/sample_plan.json --config saferclaw.config.json
```

If you do not install the package, run with:
```bash
PYTHONPATH=src python -m saferclaw <command>
```

## Defaults

- Allowed commands: `ls`, `pwd`, `find`, `cat`, `echo`, `git`
- Allowed paths: repository root (`.`)
- Network tools are denied by default (`curl`, `wget`, `ssh`, `nc`)
- Actions are written to `./.saferclaw.audit.jsonl`
- Output is truncated and confirmed by default
- Confirm prompt can be skipped with `--yes`

## Security model

1. Commands are parsed without a shell (`shlex` + `subprocess`, `shell=False`).
2. Executables must satisfy policy rules before execution.
3. File paths must stay inside configured allowed roots.
4. Optional confirmation gates stop dangerous operations.
5. All actions (attempted, skipped, blocked) are appended to an audit log.

## Repository layout

- `src/saferclaw/`: runtime package
- `examples/`: starter plan and config templates
- `docs/`: architecture and extension docs
- `AGENTS.md`-style workspace files (`AGENTS.md`, `TOOLS.md`, etc.) are supported via optional workspace profile loading

## Contributing

Contributions are expected to preserve the security defaults and add tests or clear notes when touching:
- `src/saferclaw/policy.py`
- `src/saferclaw/executor.py`
- Any file in `src/saferclaw/` that changes command or file semantics

See `CONTRIBUTING.md` for full guidance.

## License

This project is released under the MIT License. See `LICENSE`.

## Security

Report potential vulnerabilities through `SECURITY.md`.

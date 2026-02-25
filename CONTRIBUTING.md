# Contributing to SafeClaw

Thank you for helping improve SafeClaw.

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Run once:

```bash
python -m saferclaw --help
```

## Development workflow

1. Fork the repository and create a branch.
2. Make small, focused changes.
3. Keep edits scoped to safety-critical modules.
4. Update docs when behavior changes.
5. Commit with clear messages.

## Security-minded review

Changes to the following files require explicit mention of impact:

- `src/saferclaw/policy.py`
- `src/saferclaw/executor.py`
- `src/saferclaw/config.py`
- `src/saferclaw/cli.py`

If a change can affect command execution, include:
- why command/path safety remains bounded,
- which policy defaults changed,
- any new risks and mitigation.

## Style

- Keep code simple and dependency-light.
- Prefer standard library tools unless external dependency is strictly required.
- Avoid adding heavy frameworks or always-on background services.

## Pull requests

Include:
- short summary
- what is intentionally out of scope
- a short reproducible validation command

## Reporting issues

Please include:
- command and config used,
- OS / Python version,
- relevant logs from `.saferclaw.audit.jsonl`.


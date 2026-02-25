# SafeClaw

SafeClaw is a **small, local, safety-first automation agent** designed to run reliably on Raspberry Pi and other low-resource servers. It executes only policy-guarded commands and file operations, with optional LLM-assisted planning and a tiny durable queue for deferred jobs.

SafeClaw is intended for people who want practical autonomy without handing over unrestricted shell access.

![License](https://img.shields.io/badge/license-MIT-green)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Raspberry%20Pi-informational)
![Status](https://img.shields.io/badge/status-minimal%20%2B%20safe-lightgrey)

## Why SafeClaw

- Tight control over what can run (allowlist/denylist + path policy).
- Minimal dependencies and low surface area.
- No server-side persistence beyond local files/logs.
- Explicit audit trail for every attempted action.
- Open source and easy to fork for your own policy layer.

## Quick reference

Use this section when you want to start in 60 seconds:

- Install: `python -m pip install -e .`
- Initialize: `python -m saferclaw init-config --path saferclaw.config.json`
- Run command: `python -m saferclaw run "ls -la" --config saferclaw.config.json --yes`
- LLM-assisted action: `python -m saferclaw run-llm "..." --workspace examples/workspace --yes`
- Queue one job: `python -m saferclaw queue-enqueue command --payload '{"command":"ls -la"}'`

## Philosophy

SafeClaw is a **curated subset** inspired by bigger agents:

- local execution is always the only trust anchor
- LLM output is treated as intent, then constrained by policy
- all side effects are deterministic and logged
- easy to run in constrained hardware (Pi / small VPS)

## What you get

- Safe CLI command runner with confirmation + dry-run modes.
- File read/write commands with root/path restrictions.
- Optional workspace context from markdown profiles (`AGENTS.md`, `SOUL.md`, `TOOLS.md`, ...).
- Optional LLM integration (`Anthropic` / `OpenAI`) with strict tool-call execution only.
- Optional local SQLite queue for background job processing.
- Audit logging to a JSONL event log.

## Install

```bash
python -m pip install -e .
```

Or run without install:

```bash
PYTHONPATH=src python -m saferclaw --help
```

For Pi deployments, a common install pattern is a dedicated service user and writable workspace directory:

```bash
python -m pip install -e .
mkdir -p /opt/saferclaw /opt/saferclaw/.state
```

## Quick start

1. Create config:

```bash
python -m saferclaw init-config --path saferclaw.config.json
```

2. Run a safe command:

```bash
python -m saferclaw run "ls -la" --yes --config saferclaw.config.json
```

3. Run a plan file:

```bash
python -m saferclaw run-plan examples/sample_plan.json --config saferclaw.config.json
```

4. Run one LLM-assisted turn:

```bash
python -m saferclaw run-llm "List files and summarize disk usage" \
  --provider anthropic \
  --workspace examples/workspace \
  --config examples/config.example.json
```

5. Use queue mode:

```bash
python -m saferclaw queue-enqueue command --payload '{"command":"ls -la"}'
python -m saferclaw queue-run-next
python -m saferclaw queue-list
```

## Commands

### Core

- `init-config` writes a default config file.
- `run <command>` executes one safe shell command.
- `run-plan <plan_file>` executes a JSON plan.
- `run-llm <prompt>` asks the LLM for tool calls, then executes them through policy.
- `queue-enqueue`, `queue-list`, `queue-run-next` are optional background-style helpers.

### Queue

- `queue-enqueue <kind> --payload <json|file>` adds a job.
- `queue-list [--status ...] [--limit ...]` prints jobs from SQLite.
- `queue-run-next` claims and executes one queued job.

### Cheat sheet

| Goal | Command |
| --- | --- |
| Check safe command execution | `python -m saferclaw run "ls -la"` |
| Execute a plan file | `python -m saferclaw run-plan examples/sample_plan.json` |
| Ask LLM for one action | `python -m saferclaw run-llm "Show disk usage"` |
| Add queued command | `python -m saferclaw queue-enqueue command --payload '{"command":"git status --short"}'` |
| Inspect queued jobs | `python -m saferclaw queue-list --status queued --limit 20` |

Use `--config <file>` with every command while tuning your policy.

## Security model

1. Commands are parsed with `shlex` and executed with `subprocess.run(..., shell=False)`.
2. Executables are denied unless explicitly allowed.
3. File paths must be within configured root(s).
4. Network-capable binaries can be blocked independently by `network_access`.
5. Every action is written to `audit_file` in JSONL format.
6. You can skip interactive confirmation with `--yes`.

## Config

Config is JSON and loaded via `--config`.

```json
{
  "allowed_commands": ["ls", "pwd", "find", "cat", "echo", "git"],
  "denied_commands": ["curl", "wget", "ssh", "nc", "rm", "bash", "python"],
  "allowed_roots": ["."],
  "require_confirmation": true,
  "command_timeout_seconds": 8,
  "max_output_bytes": 8000,
  "audit_file": ".saferclaw.audit.jsonl",
  "network_access": false,
  "state_db_path": ".saferclaw.jobs.sqlite",
  "llm_enabled": false,
  "llm_provider": "anthropic",
  "llm_model": "claude-3-7-sonnet-latest",
  "llm_api_key_env": "ANTHROPIC_API_KEY",
  "llm_max_turns": 4
}
```

### LLM settings

- `llm_provider`: `anthropic` or `openai`.
- `llm_model`: model string for selected provider.
- `llm_api_key_env`: environment variable name used at runtime.
- `llm_max_turns`: how many chat messages are forwarded in the request.

## Markdown workspace context

When you pass `--workspace`, SafeClaw loads plain-text profiles and adds them as LLM context:

- `AGENTS.md`
- `SOUL.md`
- `TOOLS.md`
- `IDENTITY.md`
- `USER.md`
- `BOOT.md`
- `BOOTSTRAP.md`
- `MEMORY.md`
- `memory/YYYY-MM-DD.md`

These files do not execute code. They only influence the prompt the model sees.

Example:

```bash
python -m saferclaw run-llm "Summarize the pending tasks" --workspace examples/workspace
```

## Queue format

Jobs are stored in SQLite and tracked with status: `queued`, `running`, `done`, `failed`, `blocked`.

Supported kinds:

- `command`: `{ "command": "..." }`
- `read_file`: `{ "path": "..." }`
- `write_file`: `{ "path": "...", "content": "..." }`
- `plan`: `{ "steps": [ ... ] }`

Example:

```bash
python -m saferclaw queue-enqueue plan --payload '{"steps":[{"read_file":"README.md"},{"command":"git status --short"}]}'
```

## Raspberry Pi notes

SafeClaw is built to run well on small hardware:

- no heavy runtime required
- no background ML stack inside the core
- optional network calls only when using LLM mode
- SQLite queue and JSON logs keep storage simple

For Pi deployments, start with:

- `--yes` disabled until you finish allowlist tuning
- strict `allowed_roots` to your project path
- long `command_timeout_seconds` if slow filesystem operations

Example `systemd` one-shot runner:

```ini
[Unit]
Description=SafeClaw queue worker
After=network.target

[Service]
Type=oneshot
User=saferclaw
WorkingDirectory=/opt/saferclaw
ExecStart=/usr/bin/python -m pip install -e .
ExecStart=/usr/bin/python -m saferclaw queue-run-next --config /opt/saferclaw/saferclaw.config.json --yes
Environment=ANTHROPIC_API_KEY=***

[Install]
WantedBy=multi-user.target
```

Use a timer/service pair if you want periodic polling.

## Project layout

- `src/saferclaw/` runtime package
  - `cli.py` command entrypoint and command parser
  - `config.py` config loader + defaults
  - `policy.py` command/path policy enforcement
  - `executor.py` guarded execution layer
  - `workspace.py` markdown context loader
  - `llm.py` Anthropic/OpenAI adapters
  - `agent.py` tool-call execution loop
  - `queue.py` local SQLite job queue
- `docs/` architecture and contributor guides
- `examples/` starter plans and workspace profiles
- `examples/workspace/` open-claw-style markdown profiles

## Audit and observability

Logs are appended to `.saferclaw.audit.jsonl`.
Each event records at least:

- timestamp
- action kind
- command/path payload (truncated output if needed)
- status
- reason for skip/block when applicable

## Contributing

See `CONTRIBUTING.md`. In practice:

- keep `policy.py`, `executor.py` and command parsing strict by default
- add notes to docs when behavior changes
- prefer explicit behavior over broad “smart defaults”

## Troubleshooting

### `SecurityViolation: Executable is not allowlisted`

Cause: command is not present in `allowed_commands`.
Fix: add it to config and restart command with `--config`.

### `SecurityViolation: Path is outside allowed roots`

Cause: target path is outside configured workspace roots.
Fix: set `allowed_roots` in config to the exact directories you want to allow.

### `Missing API key env var`

Cause: LLM provider key variable is not exported.
Fix: `export ANTHROPIC_API_KEY=...` or `export OPENAI_API_KEY=...`.

### LLM returns `tool_calls` you did not expect

Cause: LLM prompt drift.
Fix: tighten markdown context in `--workspace`, and review `state` by forcing `--yes` off first to observe prompts.

### Queue stays in `running` forever

Cause: worker crashed after claiming a job without marking it done/failed.
Fix: rerun `queue-list`; inspect `error` and enqueue again with smaller `max_attempts`.

### “Database is locked” errors

Cause: concurrent `queue-run-next` processes.
Fix: run one worker process at a time on a Raspberry Pi, or move to serialized scheduling.

## Security reporting

Use `SECURITY.md` for vulnerability reporting instructions.

## License

MIT License. See `LICENSE`.

---

SafeClaw is intentionally opinionated: if you need more power, define additional tools intentionally rather than widening the default shell surface.

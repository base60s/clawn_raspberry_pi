# Architecture

SafeClaw is intentionally small:

1. `cli` parses user commands.
2. `config` defines runtime policy.
3. `policy` validates actions (commands and paths).
4. `executor` performs reads/writes/commands after policy checks.
5. `workspace` (optional) loads markdown context and policy hints.
6. `queue` (optional) persists jobs in SQLite.

Trust boundary:

- The LLM (if used) produces tool requests.
- The executor is the only code that runs shell or file operations.
- All actions are logged to `.saferclaw.audit.jsonl`.

Design principles:

- deterministic, explicit safe defaults
- low dependency surface
- minimal background runtime for Raspberry Pi
- easy extension points for new tools and backends


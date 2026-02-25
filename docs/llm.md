# LLM Integration Notes

SafeClaw can use a remote LLM while keeping execution safe.

Key rule:

- The LLM proposes action steps.
- `executor` validates and performs all actions.

Use:

```bash
python -m saferclaw run-llm "Check current disk usage and summarize it" \
  --provider anthropic \
  --workspace examples/workspace
```

Tool contract examples:

```json
{
  "name": "run_command",
  "arguments": { "command": "ls -la" }
}
```

```json
{
  "name": "read_file",
  "arguments": { "path": "notes.txt" }
}
```

```json
{
  "name": "write_file",
  "arguments": {
    "path": "notes.txt",
    "content": "updated text"
  }
}
```

## Required controls in SafeClaw

- schema validation before execution
- no shell=True / no command chaining
- confirmation policy
- audit logging of all tool calls and results

CLI command:

- `run-llm` (one turn)

Config-backed defaults:
- `llm_provider`
- `llm_model`
- `llm_api_key_env`
- `llm_max_turns`

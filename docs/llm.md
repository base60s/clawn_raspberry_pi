# LLM Integration Notes

SafeClaw can be extended with an LLM adapter while keeping execution safe.

Key rule:

- The LLM proposes action steps.
- `policy.py`/executor validates and performs the action.

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

## Required controls

- schema validation before execution
- no shell injection path
- confirmation policy
- audit logging of all tool calls and results


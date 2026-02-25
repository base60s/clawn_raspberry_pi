# Workspace `.md` Profiles

SafeClaw reads markdown context files from a workspace directory into LLM system prompts.

Supported files:

- `AGENTS.md` - global behavior and policy hints
- `SOUL.md` - long-term identity for agent behavior
- `TOOLS.md` - tool expectations and usage notes
- `IDENTITY.md` - role / roleplay definition
- `USER.md` - user preferences
- `BOOT.md` - startup checklist guidance
- `BOOTSTRAP.md` - initial bootstrap instructions
- `MEMORY.md` - persistent memory summary
- `memory/YYYY-MM-DD.md` - daily memory snapshots

Behavior:

- files are parsed as plain text unless frontmatter is supported.
- content is merged into `workspace_context`.
- no dynamic code execution is performed.
- malformed/missing files fall back to defaults.

Use in CLI:

```bash
python -m saferclaw run-llm "Write a short status" --workspace examples/workspace
```

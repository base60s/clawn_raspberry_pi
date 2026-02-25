# Changelog

## 0.2.0 - CLI + LLM + queue integration

- Added `run-llm` command with Anthropic and OpenAI HTTP adapters.
- Added local SQLite queue support via `queue-enqueue`, `queue-list`, and `queue-run-next`.
- Added markdown workspace context loading (`AGENTS.md`, `SOUL.md`, `TOOLS.md`, `BOOT.md`, etc.).
- Added `SafeAgent` execution loop for model tool calls.
- Added extra runtime settings to config (`llm_*`, `state_db_path`) and aligned docs.

## 0.1.0 - Initial release

- Initial Raspberry Pi-oriented safe CLI foundation.
- Safety engine with command allowlists/denylists and path sandboxing.
- Shell-free execution (`shell=False`), confirmation prompts, and audit logging.
- Optional dry-run mode and plan file execution.
- Added open source governance files and project docs scaffolding.

# Configuration

The config is JSON-based and loaded with `--config`.

Example defaults:
- `allowed_commands`
- `denied_commands`
- `allowed_roots`
- `require_confirmation`
- `command_timeout_seconds`
- `max_output_bytes`
- `audit_file`
- `network_access`
- `allowed_env`

Optional queue/llm fields (if enabled):
- `state_db_path`
- `llm_enabled`
- `llm_provider`
- `llm_model`
- `llm_api_key_env`
- `llm_max_turns`

### Resolution order

1. built-in defaults
2. JSON config file
3. CLI flags

## Environment variables

Use environment variables for credentials:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`

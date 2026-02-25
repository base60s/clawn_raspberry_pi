# Queue Mode

SafeClaw includes an optional local SQLite queue for deferred jobs.

Commands:

- `queue-enqueue`: add one job.
- `queue-list`: inspect jobs.
- `queue-run-next`: claim and run oldest queued job.

Supported job kinds:

- `command`: payload `{"command": "<shell command>"}`
- `read_file`: payload `{"path": "<path>"}`
- `write_file`: payload `{"path": "<path>", "content": "<text>"}`
- `plan`: payload `{"steps": [ ... ]}`

Example:

```bash
python -m saferclaw queue-enqueue command --payload '{"command":"ls -la"}'
python -m saferclaw queue-run-next
```

Queued jobs can be retried automatically according to `max_attempts` and are persisted in `state_db_path` by default.

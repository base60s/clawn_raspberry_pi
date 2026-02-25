# Security Model

SafeClaw defaults are restrictive:

- Allowed command list (allowlist) must include executable.
- Explicit denylist blocks known-risk executables.
- No shell chaining/operators (`&&`, `||`, `|`, `;`) are accepted.
- File operations are resolved against allowed roots.
- Confirmations are enabled by default.
- Every action writes an audit record.

Threat model:

- command injection: blocked by shell-free execution and argument parsing
- path traversal: blocked by path normalization and root checks
- accidental destructive actions: blocked via allowlist and confirmation prompts
- silent policy bypass: blocked by unified `policy.py` checks

Recommended deployment settings:

- keep denylist broad (`rm`, `sudo`, `bash`, `sh`)
- keep `require_confirmation` true
- store audit logs in persistent local storage
- prefer queue mode for long-running jobs on constrained devices


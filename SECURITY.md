# Security Policy

SafeClaw is a security-first project. If you discover a vulnerability:

1. **Do not** open a public issue for security-sensitive details.
2. Contact maintainers at `security@<your-domain-or-handle>.local`.
3. Include version, platform, and minimal reproduction.
4. Include redacted logs or config snippets.

Severity classification:

- **Critical**: unsafe execution bypass, path escaping, or audit log bypass.
- **High**: privilege escalation path, command injection via policy bypass.
- **Medium**: information leakage in logs or improper confirmation behavior.
- **Low**: documentation mismatch or incorrect defaults.

Response expectations:

- acknowledgment within 5 business days,
- initial assessment within 14 days,
- fixed release with changelog note for confirmed vulnerabilities.

For non-security bugs, use normal GitHub issues.


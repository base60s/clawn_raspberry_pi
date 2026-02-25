from __future__ import annotations

import os
import shlex
from pathlib import Path

from .config import SafetyConfig


class SecurityViolation(Exception):
    """Raised when a command or path does not satisfy the active policy."""


class CommandPolicy:
    def __init__(self, config: SafetyConfig):
        self.config = config
        self.network_executables = {
            "curl",
            "wget",
            "nc",
            "ssh",
            "ncat",
            "netcat",
            "ftp",
            "scp",
            "sftp",
        }

    @staticmethod
    def _normalize_command(command: str | list[str]) -> list[str]:
        if isinstance(command, list):
            return [str(item) for item in command if str(item).strip()]
        if isinstance(command, str):
            return shlex.split(command)
        raise TypeError("Command must be a string or list of strings")

    def validate_command(self, command: str | list[str]) -> list[str]:
        parts = self._normalize_command(command)
        if not parts:
            raise SecurityViolation("Empty command")

        executable = os.path.basename(parts[0]).lower()
        if executable in self.config.denied_commands:
            raise SecurityViolation(f"Executable is denied: {executable}")

        if executable in self.network_executables and not self.config.network_access:
            raise SecurityViolation(f"Network executable blocked by policy: {executable}")

        if self.config.allowed_commands and executable not in self.config.allowed_commands:
            raise SecurityViolation(
                f"Executable is not allowlisted: {executable}. "
                f"Enable by adding to allowed_commands."
            )

        if "&&" in parts or "||" in parts or "|" in parts or ";" in parts:
            raise SecurityViolation("Command separators/operators are not allowed")

        return parts

    def validate_path(self, path: str | Path, base: str | Path | None = None) -> Path:
        candidate = Path(path)
        if base is not None and not candidate.is_absolute():
            candidate = Path(base) / candidate
        target = candidate.resolve()
        for root in self.config.allowed_roots:
            allowed_root = Path(root).resolve()
            try:
                target.relative_to(allowed_root)
                return target
            except ValueError:
                continue
        raise SecurityViolation(
            f"Path is outside allowed roots: {target}. "
            f"Allowed roots: {', '.join(self.config.allowed_roots)}"
        )

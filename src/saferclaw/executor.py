from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import SafetyConfig
from .policy import CommandPolicy, SecurityViolation


class SafeExecutor:
    def __init__(
        self,
        config: SafetyConfig,
        dry_run: bool = False,
        auto_confirm: bool = False,
    ):
        self.config = config
        self.policy = CommandPolicy(config)
        self.dry_run = dry_run
        self.auto_confirm = auto_confirm
        self.audit_path = Path(config.audit_file)

    def _truncate(self, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) <= self.config.max_output_bytes:
            return value
        return value[: self.config.max_output_bytes] + "\n...[truncated]"

    def _record(self, event: dict[str, Any]) -> None:
        event["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")

    def _confirm(self, prompt: str) -> bool:
        if self.auto_confirm:
            return True
        return input(f"{prompt} [y/N]: ").strip().lower() in {"y", "yes"}

    def run_command(self, command: str | list[str], cwd: str | None = None) -> dict[str, Any]:
        parts = self.policy.validate_command(command)
        if self.dry_run:
            result = {
                "status": "dry_run",
                "kind": "command",
                "command": parts,
            }
            self._record(result)
            return result
        actual_cwd = Path(cwd or ".").resolve()
        self.policy.validate_path(actual_cwd)

        for argument in parts[1:]:
            if not isinstance(argument, str):
                continue
            if argument.startswith("-"):
                continue
            if any(token in argument for token in ("/", "../", "~")):
                self.policy.validate_path(argument, base=actual_cwd)

        if self.config.require_confirmation and not self.auto_confirm:
            if not self._confirm(f"Run command: {' '.join(parts)}"):
                result = {
                    "status": "skipped",
                    "kind": "command",
                    "command": parts,
                    "reason": "user_declined",
                }
                self._record(result)
                return result

        completed = subprocess.run(
            parts,
            cwd=actual_cwd,
            env=self.config.allowed_env,
            capture_output=True,
            text=True,
            timeout=self.config.command_timeout_seconds,
        )

        result = {
            "status": "ok" if completed.returncode == 0 else "failed",
            "kind": "command",
            "command": parts,
            "returncode": completed.returncode,
            "stdout": self._truncate(completed.stdout),
            "stderr": self._truncate(completed.stderr),
        }
        self._record(result)
        return result

    def read_file(self, path: str, cwd: str | None = None) -> dict[str, Any]:
        target = self.policy.validate_path(path, base=cwd)
        if self.config.require_confirmation and not self.auto_confirm and not self.dry_run:
            if not self._confirm(f"Read file: {target}"):
                result = {
                    "status": "skipped",
                    "kind": "read_file",
                    "path": str(target),
                    "reason": "user_declined",
                }
                self._record(result)
                return result

        if self.dry_run:
            result = {"status": "dry_run", "kind": "read_file", "path": str(target)}
            self._record(result)
            return result

        content = target.read_text(encoding="utf-8")
        result = {
            "status": "ok",
            "kind": "read_file",
            "path": str(target),
            "content": self._truncate(content),
        }
        self._record(result)
        return result

    def write_file(self, path: str, content: str, cwd: str | None = None) -> dict[str, Any]:
        target = self.policy.validate_path(path, base=cwd)
        if self.config.require_confirmation and not self.auto_confirm and not self.dry_run:
            if not self._confirm(f"Write file: {target}"):
                result = {
                    "status": "skipped",
                    "kind": "write_file",
                    "path": str(target),
                    "reason": "user_declined",
                }
                self._record(result)
                return result

        if self.dry_run:
            result = {"status": "dry_run", "kind": "write_file", "path": str(target)}
            self._record(result)
            return result

        target.write_text(content, encoding="utf-8")
        result = {"status": "ok", "kind": "write_file", "path": str(target)}
        self._record(result)
        return result

    def execute_plan(self, steps: list[dict[str, Any]], cwd: str | None = None) -> list[dict[str, Any]]:
        outputs = []
        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                outputs.append(
                    {
                        "status": "failed",
                        "kind": "plan_step",
                        "index": index,
                        "error": "Step is not an object",
                    }
                )
                continue

            try:
                if "command" in step:
                    outputs.append(self.run_command(step["command"], cwd=cwd))
                elif "read_file" in step:
                    outputs.append(self.read_file(step["read_file"], cwd=cwd))
                elif "write_file" in step:
                    payload = step["write_file"]
                    if not isinstance(payload, dict) or "path" not in payload or "content" not in payload:
                        raise ValueError("write_file step needs {path, content}")
                    outputs.append(
                        self.write_file(payload["path"], str(payload["content"]), cwd=cwd)
                    )
                else:
                    outputs.append(
                        {
                            "status": "failed",
                            "kind": "plan_step",
                            "index": index,
                            "error": "Step missing command/read_file/write_file",
                        }
                    )
            except SecurityViolation as err:
                outputs.append(
                    {
                        "status": "blocked",
                        "kind": "plan_step",
                        "index": index,
                        "error": str(err),
                    }
                )
            except Exception as err:
                outputs.append(
                    {
                        "status": "failed",
                        "kind": "plan_step",
                        "index": index,
                        "error": str(err),
                    }
                )
        return outputs

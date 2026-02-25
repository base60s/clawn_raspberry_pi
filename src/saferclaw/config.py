from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Mapping


DEFAULT_ALLOWED_COMMANDS = ["ls", "pwd", "find", "cat", "echo", "git"]
DEFAULT_DENIED_COMMANDS = [
    "curl",
    "wget",
    "ssh",
    "nc",
    "sudo",
    "rm",
    "rmdir",
    "bash",
    "sh",
    "python",
    "node",
    "deno",
]


@dataclass
class SafetyConfig:
    allowed_commands: set[str] = field(default_factory=lambda: set(DEFAULT_ALLOWED_COMMANDS))
    denied_commands: set[str] = field(default_factory=lambda: set(DEFAULT_DENIED_COMMANDS))
    allowed_roots: list[str] = field(default_factory=lambda: [str(Path(".").resolve())]
    require_confirmation: bool = True
    command_timeout_seconds: int = 10
    max_output_bytes: int = 12_000
    audit_file: str = ".saferclaw.audit.jsonl"
    network_access: bool = False
    allowed_env: dict[str, str] = field(
        default_factory=lambda: {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"}
    )

    def dump(self) -> str:
        payload = asdict(self)
        payload["allowed_commands"] = sorted(payload["allowed_commands"])
        payload["denied_commands"] = sorted(payload["denied_commands"])
        return json.dumps(payload, indent=2)


def _coerce_set(value: object) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, list):
        return set(str(item).strip().lower() for item in value if str(item).strip())
    raise ValueError("Expected a list of strings")


def _coerce_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raise ValueError("Expected a list of strings")


def _coerce_bool(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


def _coerce_int(value: object, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise ValueError("Expected an integer")


def load_config(path: str | None = None) -> SafetyConfig:
    if path is None:
        return SafetyConfig()

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    if not isinstance(raw, Mapping):
        raise ValueError("Config file must contain an object")

    allowed_commands = _coerce_set(raw.get("allowed_commands")) or set(
        DEFAULT_ALLOWED_COMMANDS
    )
    denied_commands = _coerce_set(raw.get("denied_commands")) or set(
        DEFAULT_DENIED_COMMANDS
    )
    allowed_roots = _coerce_list(raw.get("allowed_roots"))
    if not allowed_roots:
        allowed_roots = [str(Path(".").resolve())]

    return SafetyConfig(
        allowed_commands=allowed_commands,
        denied_commands=denied_commands,
        allowed_roots=allowed_roots,
        require_confirmation=_coerce_bool(
            raw.get("require_confirmation"), SafetyConfig.require_confirmation
        ),
        command_timeout_seconds=_coerce_int(
            raw.get("command_timeout_seconds"), SafetyConfig.command_timeout_seconds
        ),
        max_output_bytes=_coerce_int(raw.get("max_output_bytes"), SafetyConfig.max_output_bytes),
        audit_file=str(raw.get("audit_file") or SafetyConfig.audit_file),
        network_access=_coerce_bool(raw.get("network_access"), SafetyConfig.network_access),
        allowed_env=(
            {str(k): str(v) for k, v in raw.get("allowed_env").items()}
            if isinstance(raw.get("allowed_env"), dict)
            else SafetyConfig.allowed_env.copy()
        ),
    )


def write_default_config(path: str) -> None:
    config = SafetyConfig()
    Path(path).write_text(config.dump(), encoding="utf-8")

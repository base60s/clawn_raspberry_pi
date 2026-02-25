from __future__ import annotations

from pathlib import Path

PROFILE_FILES = [
    "AGENTS.md",
    "SOUL.md",
    "TOOLS.md",
    "IDENTITY.md",
    "USER.md",
    "BOOT.md",
    "BOOTSTRAP.md",
    "MEMORY.md",
]


def load_workspace_profiles(workspace_dir: str | None) -> dict[str, str]:
    root = Path(workspace_dir or ".").resolve()
    if not root.exists():
        raise FileNotFoundError(f"Workspace not found: {root}")

    profiles: dict[str, str] = {}
    for filename in PROFILE_FILES:
        path = root / filename
        if path.exists() and path.is_file():
            content = path.read_text(encoding="utf-8").strip()
            if content:
                profiles[filename] = content

    memory_dir = root / "memory"
    if memory_dir.exists() and memory_dir.is_dir():
        entries = sorted(memory_dir.glob("*.md"))
        for path in entries:
            content = path.read_text(encoding="utf-8").strip()
            if content:
                profiles[f"MEMORY:{path.name}"] = content

    return profiles


def workspace_context_text(
    workspace_dir: str | None,
    extra: dict[str, str] | None = None,
) -> str:
    profiles = load_workspace_profiles(workspace_dir) if workspace_dir else {}
    if extra:
        for key, value in extra.items():
            if value is not None:
                profiles[key] = value
    if not profiles:
        return ""

    parts: list[str] = []
    for key in PROFILE_FILES:
        value = profiles.get(key)
        if value:
            parts.append(f"## {key}\n\n{value}")

    for key in sorted(name for name in profiles if name.startswith("MEMORY:")):
        parts.append(f"## {key}\n\n{profiles[key]}")

    return "\n\n".join(parts)

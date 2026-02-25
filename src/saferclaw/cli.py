from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .config import load_config, write_default_config
from .executor import SafeExecutor


def _load_plan(path: str) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("steps"), list):
        return data["steps"]
    if isinstance(data, list):
        return data
    raise ValueError("Plan must be a list or an object containing a 'steps' list")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="saferclaw",
        description="Small, safe local agent for controlled command/file execution.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to JSON config file (default built-in policy).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would run without executing commands or modifying files.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip all confirmation prompts.",
    )
    parser.add_argument(
        "--cwd",
        default=None,
        help="Optional working directory for command execution.",
    )

    subcommands = parser.add_subparsers(dest="command", required=True)

    init_cmd = subcommands.add_parser(
        "init-config", help="Write a default config file."
    )
    init_cmd.add_argument(
        "--path",
        default=".saferclaw.config.json",
        help="Where to write the config file.",
    )

    run_cmd = subcommands.add_parser(
        "run", help="Run a single command or a shell-safe command string."
    )
    run_cmd.add_argument(
        "command_line",
        nargs="+",
        help="Command to run, e.g. saferclaw run \"ls -la\"",
    )

    plan_cmd = subcommands.add_parser(
        "run-plan", help="Execute a JSON plan file with multiple steps."
    )
    plan_cmd.add_argument("plan", help="Path to plan JSON file.")
    plan_cmd.add_argument(
        "--cwd",
        default=None,
        help="Optional working directory for command steps.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)
    executor = SafeExecutor(
        config=config,
        dry_run=args.dry_run,
        auto_confirm=args.yes,
    )

    if args.command == "init-config":
        write_default_config(args.path)
        print(f"Wrote config template to {args.path}")
        return 0

    if args.command == "run":
        command = " ".join(args.command_line)
        result = executor.run_command(command, cwd=args.cwd)
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") in {"ok", "dry_run", "skipped"} else 1

    if args.command == "run-plan":
        steps = _load_plan(args.plan)
        results = executor.execute_plan(steps, cwd=args.cwd)
        print(json.dumps(results, indent=2))
        failed = [r for r in results if r.get("status") in {"failed", "blocked"}]
        return 0 if not failed else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from dataclasses import asdict

from .config import load_config, write_default_config
from .executor import SafeExecutor
from .agent import AgentError, SafeAgent
from .llm import AnthropicHTTPClient, LLMError, OpenAIHTTPClient
from .policy import SecurityViolation
from .queue import Job, QueueManager
from .workspace import workspace_context_text


def _load_plan(path: str) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("steps"), list):
        return data["steps"]
    if isinstance(data, list):
        return data
    raise ValueError("Plan must be a list or an object containing a 'steps' list")


def _load_json_payload(payload: str) -> dict[str, Any]:
    path = Path(payload)
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
    else:
        raw = json.loads(payload)
    if not isinstance(raw, dict):
        raise ValueError("Payload must be a JSON object")
    return raw


def _to_llm_client(args: Any, config: Any):
    provider = (args.provider or config.llm_provider).strip().lower()
    model = args.model or config.llm_model
    if provider == "openai":
        default_env = "OPENAI_API_KEY"
        default_model = "gpt-4o-mini"
        if model is None:
            model = "gpt-4o-mini"
        return OpenAIHTTPClient(
            model=model or default_model,
            api_key_env=args.api_key_env or config.llm_api_key_env or default_env,
        )
    provider = "anthropic" if provider == "auto" else provider
    default_env = "ANTHROPIC_API_KEY"
    default_model = "claude-3-7-sonnet-latest"
    return AnthropicHTTPClient(
        model=model or config.llm_model or default_model,
        api_key_env=args.api_key_env or config.llm_api_key_env or default_env,
    )


def _job_to_dict(job: Job) -> dict[str, Any]:
    data = asdict(job)
    return data


def _run_job(kind: str, payload: Any, executor: SafeExecutor, cwd: str | None = None) -> dict[str, Any]:
    if kind == "command":
        command = payload.get("command", payload.get("value"))
        if not isinstance(command, str) or not command.strip():
            raise ValueError("Command job requires a non-empty 'command'")
        return executor.run_command(command, cwd=cwd)

    if kind == "read_file":
        path = payload.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ValueError("read_file job requires 'path'")
        return executor.read_file(path, cwd=cwd)

    if kind == "write_file":
        path = payload.get("path")
        content = payload.get("content")
        if not isinstance(path, str) or not path.strip():
            raise ValueError("write_file job requires 'path'")
        if content is None:
            raise ValueError("write_file job requires 'content'")
        return executor.write_file(path, str(content), cwd=cwd)

    if kind == "plan":
        if isinstance(payload, list):
            steps = payload
        else:
            steps = payload.get("steps")
        if not isinstance(steps, list):
            raise ValueError("plan job requires list in 'steps'")
        return {"status": "ok", "kind": "plan", "results": executor.execute_plan(steps, cwd=cwd)}

    raise ValueError(f"Unknown job kind: {kind}")


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

    run_llm_cmd = subcommands.add_parser(
        "run-llm", help="Generate and execute one safe action turn from an LLM."
    )
    run_llm_cmd.add_argument("prompt", nargs="+", help="Prompt passed to the LLM.")
    run_llm_cmd.add_argument(
        "--provider",
        default="auto",
        choices=["auto", "anthropic", "openai"],
        help="LLM provider (default: auto using config).",
    )
    run_llm_cmd.add_argument("--model", default=None, help="Model override.")
    run_llm_cmd.add_argument("--api-key-env", default=None, help="Env var for provider key.")
    run_llm_cmd.add_argument(
        "--max-turns",
        type=int,
        default=None,
        help="Max turns/messages passed to provider.",
    )
    run_llm_cmd.add_argument(
        "--workspace",
        default=None,
        help="Path containing AGENTS.md and other SafeClaw markdown context files.",
    )
    run_llm_cmd.add_argument(
        "--cwd",
        default=None,
        help="Working directory for generated tool calls.",
    )

    queue_enqueue_cmd = subcommands.add_parser("queue-enqueue", help="Enqueue a new safe job.")
    queue_enqueue_cmd.add_argument("kind", help="Job kind: command | read_file | write_file | plan")
    queue_enqueue_cmd.add_argument("--payload", required=True, help="JSON object or path to JSON file.")
    queue_enqueue_cmd.add_argument(
        "--db",
        default=None,
        help="SQLite job database path (default from config).",
    )
    queue_enqueue_cmd.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Maximum retry attempts.",
    )

    queue_list_cmd = subcommands.add_parser("queue-list", help="List queued jobs.")
    queue_list_cmd.add_argument("--db", default=None, help="SQLite job database path.")
    queue_list_cmd.add_argument("--status", default=None, help="Filter by status.")
    queue_list_cmd.add_argument("--limit", type=int, default=50, help="Max rows.")

    queue_run_cmd = subcommands.add_parser(
        "queue-run-next",
        help="Claim the oldest queued job and run it.",
    )
    queue_run_cmd.add_argument(
        "--db",
        default=None,
        help="SQLite job database path (default from config).",
    )
    queue_run_cmd.add_argument(
        "--cwd",
        default=None,
        help="Working directory for generated tool calls.",
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

    if args.command == "run-llm":
        if not config.llm_enabled and args.provider == "auto":
            config.llm_enabled = True
        workspace_context = workspace_context_text(args.workspace)
        try:
            llm = _to_llm_client(args, config)
            agent = SafeAgent(executor, llm, workspace_context=workspace_context)
            result = agent.run(
                " ".join(args.prompt),
                cwd=args.cwd,
                max_turns=args.max_turns or config.llm_max_turns,
            )
            print(json.dumps(result, indent=2))
            return 0
        except (LLMError, SecurityViolation, ValueError, AgentError, FileNotFoundError) as err:
            print(json.dumps({"status": "failed", "error": str(err)}, indent=2))
            return 1

    if args.command == "queue-enqueue":
        payload = _load_json_payload(args.payload)
        manager = QueueManager(args.db or config.state_db_path)
        job_id = manager.enqueue(args.kind, payload, max_attempts=args.max_attempts)
        manager.close()
        print(json.dumps({"status": "queued", "job_id": job_id}, indent=2))
        return 0

    if args.command == "queue-list":
        manager = QueueManager(args.db or config.state_db_path)
        jobs = [_job_to_dict(item) for item in manager.list_jobs(args.status, limit=args.limit)]
        manager.close()
        print(json.dumps(jobs, indent=2))
        return 0

    if args.command == "queue-run-next":
        manager = QueueManager(args.db or config.state_db_path)
        job = manager.claim_next()
        if job is None:
            manager.close()
            print(json.dumps({"status": "idle", "jobs": 0}, indent=2))
            return 0

        try:
            output = _run_job(job.kind, job.payload, executor, cwd=args.cwd)
            manager.mark_done(job.id, json.dumps(output))
            manager.close()
            print(json.dumps({"status": "done", "job_id": job.id, "output": output}, indent=2))
            return 0 if output.get("status") == "ok" else 1
        except SecurityViolation as err:
            manager.mark_blocked(job.id, str(err))
            manager.close()
            print(json.dumps({"status": "blocked", "job_id": job.id, "error": str(err)}, indent=2))
            return 1
        except Exception as err:
            manager.mark_failed(job.id, str(err), retryable=True)
            manager.close()
            print(json.dumps({"status": "failed", "job_id": job.id, "error": str(err)}, indent=2))
            return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

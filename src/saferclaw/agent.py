from __future__ import annotations

from typing import Any

from .executor import SafeExecutor
from .llm import LLMClient, ToolRequest, default_tool_schemas


class AgentError(RuntimeError):
    """Raised when the safe agent cannot execute a model tool request."""


class SafeAgent:
    """Run model-produced tool calls through SafeExecutor."""

    def __init__(
        self,
        executor: SafeExecutor,
        llm_client: LLMClient,
        workspace_context: str = "",
    ):
        self.executor = executor
        self.llm = llm_client
        self.workspace_context = workspace_context.strip()

    def run(self, prompt: str, cwd: str | None = None, max_turns: int = 1) -> dict[str, Any]:
        if not prompt.strip():
            raise AgentError("Prompt is empty")

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a safe local execution agent. "
                    "You can only execute allowed local tools listed below."
                ),
            },
            {"role": "system", "content": "Allowed tools: run_command, read_file, write_file, run_plan."},
        ]
        if self.workspace_context:
            messages.append(
                {
                    "role": "system",
                    "content": f"Workspace profile:\n\n{self.workspace_context}",
                }
            )
        messages.append({"role": "user", "content": prompt})

        response = self.llm.complete(messages, default_tool_schemas(), max_turns=max_turns)
        tool_outputs = []
        status = "ok"
        for tool in response.tool_calls:
            output = self._execute_tool(tool, cwd=cwd)
            tool_outputs.append(output)
            if output.get("status") in {"failed", "blocked"}:
                status = "failed"

        return {
            "status": status,
            "llm_content": response.content,
            "stop_reason": response.stop_reason,
            "tool_calls": [self._tool_to_dict(tool) for tool in response.tool_calls],
            "tool_outputs": tool_outputs,
        }

    @staticmethod
    def _tool_to_dict(tool: ToolRequest) -> dict[str, Any]:
        return {"name": tool.name, "arguments": tool.arguments}

    def _execute_tool(self, tool: ToolRequest, cwd: str | None) -> dict[str, Any]:
        name = (tool.name or "").strip()
        args = tool.arguments or {}
        if not isinstance(args, dict):
            raise AgentError(f"Tool arguments must be an object: {name}")

        if name == "run_command":
            command = args.get("command")
            if not command:
                raise AgentError("run_command requires 'command'")
            return self.executor.run_command(str(command), cwd=cwd)
        if name == "read_file":
            path = args.get("path")
            if not path:
                raise AgentError("read_file requires 'path'")
            return self.executor.read_file(str(path), cwd=cwd)
        if name == "write_file":
            path = args.get("path")
            if path is None or "content" not in args:
                raise AgentError("write_file requires 'path' and 'content'")
            return self.executor.write_file(str(path), str(args.get("content", "")), cwd=cwd)
        if name == "run_plan":
            raw_steps = args.get("steps")
            if not isinstance(raw_steps, list):
                raise AgentError("run_plan requires 'steps' as a list")
            return {
                "status": "ok",
                "kind": "run_plan",
                "results": self.executor.execute_plan(raw_steps, cwd=cwd),
            }
        raise AgentError(f"Unknown tool: {name}")

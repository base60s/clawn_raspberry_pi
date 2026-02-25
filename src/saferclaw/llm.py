from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


class LLMError(RuntimeError):
    """Raised when provider request/response cannot be processed."""


@dataclass
class ToolRequest:
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[ToolRequest]
    stop_reason: str | None = None


class LLMClient(Protocol):
    def complete(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        max_turns: int = 1,
    ) -> LLMResponse:
        ...


class BaseLLMClient:
    def __init__(self, api_url: str, api_key_env: str, timeout_sec: int = 30):
        self.api_url = api_url
        self.api_key_env = api_key_env
        self.timeout_sec = timeout_sec

    def _http_post(self, payload: dict[str, Any]) -> dict[str, Any]:
        key = os.getenv(self.api_key_env)
        if not key:
            raise LLMError(f"Missing API key env var: {self.api_key_env}")
        request = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            method="POST",
        )
        context = ssl.create_default_context()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_sec, context=context) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as err:
            detail = ""
            try:
                detail = err.read().decode("utf-8")
            except Exception:
                detail = ""
            raise LLMError(f"LLM HTTP error {err.code}: {detail}") from err
        except urllib.error.URLError as err:
            raise LLMError(f"LLM network error: {err}") from err
        except Exception as err:
            raise LLMError(f"LLM request failed: {err}") from err


class AnthropicHTTPClient(BaseLLMClient):
    def __init__(
        self,
        model: str = "claude-3-7-sonnet-latest",
        api_key_env: str = "ANTHROPIC_API_KEY",
        timeout_sec: int = 30,
        api_url: str = "https://api.anthropic.com/v1/messages",
    ):
        super().__init__(api_url, api_key_env=api_key_env, timeout_sec=timeout_sec)
        self.model = model

    def _system_prompt(self, tools: list[dict[str, Any]]) -> str:
        names = [tool.get("name", "unknown") for tool in tools]
        return (
            "You are a safe local agent. Return tool calls only for allowed actions. "
            f"Allowed tools: {', '.join(names)}"
        )

    def complete(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        max_turns: int = 1,
    ) -> LLMResponse:
        if max_turns < 1:
            max_turns = 1

        prompt_tools = [self._to_anthropic_tool(tool) for tool in tools]
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 1024,
            "system": self._system_prompt(tools),
            "messages": messages[:max_turns],
            "tools": prompt_tools,
        }

        data = self._http_post(payload)
        content = ""
        tool_calls: list[ToolRequest] = []
        for block in data.get("content", []):
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                content += str(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    ToolRequest(
                        name=str(block.get("name", "")),
                        arguments=_coerce_args(block.get("input")),
                    )
                )
        return LLMResponse(
            content=content.strip(),
            tool_calls=tool_calls,
            stop_reason=data.get("stop_reason"),
        )

    def _to_anthropic_tool(self, tool: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": str(tool.get("name", "")),
            "description": str(tool.get("description", "")),
            "input_schema": tool.get("input_schema", {"type": "object", "properties": {}}),
        }


class OpenAIHTTPClient(BaseLLMClient):
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key_env: str = "OPENAI_API_KEY",
        timeout_sec: int = 30,
        api_url: str = "https://api.openai.com/v1/chat/completions",
    ):
        super().__init__(api_url, api_key_env=api_key_env, timeout_sec=timeout_sec)
        self.model = model

    def complete(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        max_turns: int = 1,
    ) -> LLMResponse:
        if max_turns < 1:
            max_turns = 1
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages[:max_turns],
            "tools": [self._to_openai_tool(tool) for tool in tools],
            "tool_choice": "auto",
            "max_tokens": 1024,
        }
        data = self._http_post(payload)
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {}) if isinstance(choice, dict) else {}
        content = str(message.get("content", "") or "")
        tool_calls: list[ToolRequest] = []
        for tool_call in message.get("tool_calls", []) if isinstance(message, dict) else []:
            if not isinstance(tool_call, dict):
                continue
            function = tool_call.get("function", {})
            if not isinstance(function, dict):
                continue
            tool_calls.append(
                ToolRequest(
                    name=str(function.get("name", "")),
                    arguments=_coerce_args(function.get("arguments")),
                )
            )
        return LLMResponse(content=content.strip(), tool_calls=tool_calls, stop_reason="tool_calls")

    def _to_openai_tool(self, tool: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": str(tool.get("name", "")),
                "description": str(tool.get("description", "")),
                "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
            },
        }


def _coerce_args(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            loaded = json.loads(raw)
            return loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def default_tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "name": "run_command",
            "description": "Run a safe shell command with allowlist policy.",
            "input_schema": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
        {
            "name": "read_file",
            "description": "Read a text file from an allowed path.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
        {
            "name": "write_file",
            "description": "Write UTF-8 text to an allowed path.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
        {
            "name": "run_plan",
            "description": "Execute an ordered plan with steps.",
            "input_schema": {
                "type": "object",
                "properties": {"steps": {"type": "array"}},
                "required": ["steps"],
            },
        },
    ]


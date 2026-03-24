import json
import os
from typing import Any

import litellm

from knowledge_core.config import settings
from knowledge_core.ports.llm_port import LLMPort


def _resolve_setting(dynaconf_value: str, env_var_fallback: str) -> str:
    """Return dynaconf value if non-empty, else fall back to an env var."""
    if dynaconf_value:
        return dynaconf_value
    return os.environ.get(env_var_fallback, "")


class LLMClient(LLMPort):
    """LiteLLM wrapper implementing the LLM port interface."""

    def __init__(self) -> None:
        self._api_base = _resolve_setting(settings.llm.api_url, "LITE_LLM_PROXY_API_URL")
        self._api_key = _resolve_setting(settings.llm.api_key, "LITE_LLM_PROXY_API_KEY")
        self._default_model = settings.llm.chat_model

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> str:
        """Send a completion request and return the text response."""
        response = await litellm.acompletion(
            model=model or self._default_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            api_base=self._api_base,
            api_key=self._api_key,
        )
        return response.choices[0].message.content

    async def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Send a completion request with tool definitions, return full response."""
        response = await litellm.acompletion(
            model=model or self._default_model,
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            api_base=self._api_base,
            api_key=self._api_key,
        )
        message = response.choices[0].message
        result: dict[str, Any] = {
            "role": "assistant",
            "content": message.content or "",
        }
        if message.tool_calls:
            result["tool_calls"] = [
                self._parse_tool_call(tool_call) for tool_call in message.tool_calls
            ]
        return result

    def _parse_tool_call(self, tool_call: Any) -> dict[str, Any]:
        """Parse a single tool call from the LLM response."""
        raw_arguments = tool_call.function.arguments
        parsed_arguments = (
            json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
        )
        return {
            "id": tool_call.id,
            "type": "function",
            "function": {
                "name": tool_call.function.name,
                "arguments": parsed_arguments,
            },
        }

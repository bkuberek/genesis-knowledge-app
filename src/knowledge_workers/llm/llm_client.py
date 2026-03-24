import json
from typing import Any

import litellm

from knowledge_core.config import settings
from knowledge_core.ports.llm_port import LLMPort


class LLMClient(LLMPort):
    """LiteLLM wrapper implementing the LLM port interface."""

    def __init__(self) -> None:
        self._api_base = settings.llm.api_url
        self._api_key = settings.llm.api_key
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

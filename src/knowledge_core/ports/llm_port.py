import abc
from typing import Any


class LLMPort(abc.ABC):
    """Abstract interface for LLM operations."""

    @abc.abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> str:
        """Send a completion request and return the text response."""
        ...

    @abc.abstractmethod
    async def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Send a completion request with tool definitions, return full response."""
        ...

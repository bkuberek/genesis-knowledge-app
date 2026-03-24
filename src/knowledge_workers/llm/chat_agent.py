"""Chat agent with tool-calling loop — no LangChain."""

import json
from typing import Any

from knowledge_core.ports.database_repository_port import DatabaseRepositoryPort
from knowledge_core.ports.llm_port import LLMPort

MAX_TOOL_ROUNDS = 5

SYSTEM_PROMPT = (
    "You are a knowledge assistant. You help users query and understand their data.\n"
    "You have access to tools that let you search, filter, and aggregate entities "
    "stored in the database.\n"
    "Always start by calling describe_tables to understand what data is available.\n"
    "Use the tools to find precise answers, then explain the results clearly.\n"
    "Cite specific data points in your answers."
)


class ChatAgent:
    """Orchestrates LLM tool-calling rounds against the database."""

    def __init__(
        self,
        llm_client: LLMPort,
        repository: DatabaseRepositoryPort,
    ) -> None:
        self._llm = llm_client
        self._repository = repository

    async def process_message(
        self,
        user_message: str,
        conversation_history: list[dict[str, Any]],
    ) -> str:
        """Process a user message through the tool-calling loop."""
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        tools = self._get_tool_definitions()

        for _round in range(MAX_TOOL_ROUNDS):
            response = await self._llm.complete_with_tools(
                messages=messages,
                tools=tools,
            )

            if not response.get("tool_calls"):
                return response.get("content", "I couldn't generate a response.")

            messages.append(response)

            for tool_call in response["tool_calls"]:
                result = await self._execute_tool(tool_call)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(result),
                    }
                )

        # Hit max rounds — force a text response with empty tools
        response = await self._llm.complete_with_tools(
            messages=messages,
            tools=[],
        )
        return response.get(
            "content",
            "I used all available tool calls. Here's what I found so far.",
        )

    # -- Tool execution ---------------------------------------------------

    async def _execute_tool(self, tool_call: dict) -> Any:
        """Execute a single tool call and return the result."""
        name = tool_call["function"]["name"]
        raw_args = tool_call["function"]["arguments"]
        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args

        handler = self._tool_map().get(name)
        if handler is None:
            return {"error": f"Unknown tool: {name}"}

        try:
            return await handler(args)
        except Exception as exc:
            return {"error": str(exc)}

    def _tool_map(self) -> dict[str, Any]:
        return {
            "describe_tables": self._tool_describe_tables,
            "query_data": self._tool_query_data,
            "aggregate_data": self._tool_aggregate_data,
            "search_entities": self._tool_search_entities,
        }

    # -- Tool handlers ----------------------------------------------------

    async def _tool_describe_tables(self, args: dict) -> dict:
        return await self._repository.describe_entity_schema()

    async def _tool_query_data(self, args: dict) -> dict:
        entities = await self._repository.query_entities(
            entity_type=args.get("entity_type"),
            filters=args.get("filters"),
            sort_by=args.get("sort_by"),
            sort_order=args.get("sort_order", "asc"),
            limit=args.get("limit", 20),
        )
        return {
            "results": [e.model_dump() for e in entities],
            "count": len(entities),
        }

    async def _tool_aggregate_data(self, args: dict) -> dict:
        results = await self._repository.aggregate_entities(
            entity_type=args.get("entity_type"),
            property_name=args.get("property_name"),
            operation=args.get("operation", "count"),
            group_by=args.get("group_by"),
        )
        return {"results": results}

    async def _tool_search_entities(self, args: dict) -> dict:
        entities = await self._repository.search_entities(
            query=args.get("query", ""),
            entity_type=args.get("entity_type"),
            limit=args.get("limit", 20),
        )
        return {
            "results": [e.model_dump() for e in entities],
            "count": len(entities),
        }

    # -- Tool definitions -------------------------------------------------

    def _get_tool_definitions(self) -> list[dict]:
        """Return OpenAI-compatible tool definitions for the LLM."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "describe_tables",
                    "description": (
                        "Get available entity types and their JSONB "
                        "property keys/types. Call this first to "
                        "understand what data is available."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "query_data",
                    "description": (
                        "Query entities by type with optional filters on "
                        "JSONB properties. Supports comparison operators "
                        "(=, !=, >, <, >=, <=, contains, like) and sorting."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity_type": {
                                "type": "string",
                                "description": (
                                    "Filter by entity type (e.g., 'company', 'person')"
                                ),
                            },
                            "filters": {
                                "type": "array",
                                "description": "List of filter conditions",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "property": {
                                            "type": "string",
                                            "description": ("JSONB property name"),
                                        },
                                        "operator": {
                                            "type": "string",
                                            "enum": [
                                                "=",
                                                "!=",
                                                ">",
                                                "<",
                                                ">=",
                                                "<=",
                                                "contains",
                                                "like",
                                            ],
                                        },
                                        "value": {
                                            "description": ("Value to compare against"),
                                        },
                                    },
                                    "required": [
                                        "property",
                                        "operator",
                                        "value",
                                    ],
                                },
                            },
                            "sort_by": {
                                "type": "string",
                                "description": ("JSONB property name to sort by"),
                            },
                            "sort_order": {
                                "type": "string",
                                "enum": ["asc", "desc"],
                                "default": "asc",
                            },
                            "limit": {
                                "type": "integer",
                                "default": 20,
                                "maximum": 100,
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "aggregate_data",
                    "description": (
                        "Compute aggregates (avg, sum, count, min, max) "
                        "on numeric JSONB properties, optionally grouped "
                        "by another property."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity_type": {
                                "type": "string",
                                "description": "Entity type to aggregate",
                            },
                            "property_name": {
                                "type": "string",
                                "description": ("Numeric JSONB property to aggregate"),
                            },
                            "operation": {
                                "type": "string",
                                "enum": [
                                    "count",
                                    "avg",
                                    "sum",
                                    "min",
                                    "max",
                                ],
                            },
                            "group_by": {
                                "type": "string",
                                "description": ("JSONB property to group results by"),
                            },
                        },
                        "required": ["operation"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_entities",
                    "description": (
                        "Full-text search on entity names. Use when "
                        "looking for specific entities by name."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query text",
                            },
                            "entity_type": {
                                "type": "string",
                                "description": "Optional type filter",
                            },
                            "limit": {
                                "type": "integer",
                                "default": 20,
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
        ]

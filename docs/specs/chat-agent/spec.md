# Chat Agent — Specification

**Phase**: 6
**Status**: Implemented (retroactive spec)
**Change**: chat-agent

## Intent

Implement the conversational chat agent with a tool-calling loop that lets users query the
knowledge database in natural language. The agent uses LLM tool calls to search entities,
query/filter by properties, and compute aggregations — without LangChain or any agent
framework.

## Key Requirements

### REQ-6.1: Tool-Calling Loop

**GIVEN** a user sends a chat message
**WHEN** the chat agent processes it
**THEN** `ChatAgent.process_message()` must: build a message list with system prompt and
conversation history, call the LLM with tool definitions, execute any tool calls returned,
append tool results, and loop until the LLM returns a text response (no tool calls) or
`MAX_TOOL_ROUNDS` (5) is reached.

### REQ-6.2: Four Database Tools

**GIVEN** the agent needs to query the knowledge base
**WHEN** the LLM selects a tool
**THEN** four tools must be available:
- `describe_tables` — Returns entity types and their JSONB property keys/types
- `query_data` — Queries entities by type with optional JSONB filters, sorting, and limit
- `aggregate_data` — Computes aggregates (count, avg, sum, min, max) with optional group_by
- `search_entities` — Full-text search on entity names

### REQ-6.3: Filter Syntax

**GIVEN** the `query_data` tool supports property filtering
**WHEN** the LLM constructs a filter
**THEN** each filter must be an object with `property`, `operator`, and `value` fields.
Supported operators: `=`, `!=`, `>`, `<`, `>=`, `<=`, `contains`, `like`.

### REQ-6.4: System Prompt with Tool Selection Guide

**GIVEN** the LLM needs guidance to choose the right tool
**WHEN** the agent builds the message list
**THEN** the system prompt must include: a workflow section (call `describe_tables` first),
a tool selection guide with examples mapping question types to tools, filter syntax
documentation, and instructions to always provide data-backed answers.

### REQ-6.5: Max Tool Rounds Safety

**GIVEN** the LLM might loop indefinitely with tool calls
**WHEN** `MAX_TOOL_ROUNDS` (5) is reached without a text response
**THEN** the agent must force a final LLM call with empty tools to get a text response.

### REQ-6.6: Dynaconf Settings Fix

**GIVEN** dynaconf's `@format {this.VAR|default}` pipe syntax is unreliable
**WHEN** the application reads LLM configuration
**THEN** `settings.toml` must use plain default values and `_resolve_setting()` must
check the dynaconf value first, falling back to direct env var reads.

### REQ-6.7: WebSocket Integration

**GIVEN** the WebSocket handler previously had a stub response
**WHEN** Phase 6 is implemented
**THEN** the WebSocket handler must integrate with `ChatAgent`, passing conversation history
(excluding the current user message, which the agent adds) to `process_message()`.

## Implementation Summary

### Files Created/Modified

- `settings.toml` — Replaced `@format` with plain default values
- `src/knowledge_workers/llm/llm_client.py` — Added env var fallback via `_resolve_setting()`
- `src/knowledge_workers/llm/chat_agent.py` — ChatAgent with 4 tools, tool-calling loop
- `src/knowledge_workers/llm/__init__.py` — Exports ChatAgent
- `src/knowledge_api/dependencies/container.py` — Wires ChatAgent into DI container
- `src/knowledge_api/routers/websocket_handler.py` — Replaced stub with real agent integration
- `tests/unit/test_chat_agent.py` — 15 comprehensive unit tests

### Key Patterns & Decisions

- No LangChain — vanilla Python loop with LLM tool-calling protocol
- System prompt is detailed to guide LLM toward correct tool selection, reducing round trips
- `conversation_history[:-1]` passed to agent because the current user message is added
  separately by the agent itself
- Tool call arguments can arrive as `str` or `dict` — `isinstance` check handles both

## Discoveries

- dynaconf's `@format {this.VAR|default}` pipe syntax does not reliably resolve defaults;
  plain defaults with env var override via `KNOWLEDGE_` prefix work better
- The WebSocket handler passes `conversation_history[:-1]` to `process_message` since the
  current user message is added separately by the agent
- `aggregate_entities` doesn't support a `filters` param — the system prompt guides the LLM
  to use `query_data` for filtered aggregations

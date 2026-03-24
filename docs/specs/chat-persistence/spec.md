# Chat Persistence & Query Refinement — Specification

**Phase**: 9–10
**Status**: Implemented (retroactive spec)
**Change**: chat-persistence

## Intent

Polish the chat experience with two improvements: (1) enhanced system prompt that guides
the LLM to select the right database tool with detailed examples and filter syntax, and
(2) automatic session title generation from the first user message, with real-time title
updates pushed to the frontend via WebSocket.

## Key Requirements

### REQ-9.1: Enhanced System Prompt

**GIVEN** the chat agent's tool selection was imprecise
**WHEN** the system prompt is improved
**THEN** the `SYSTEM_PROMPT` must include: a workflow section (always call `describe_tables`
first), a tool selection guide mapping question types to specific tools with examples, filter
syntax documentation with operator examples, and explicit instructions for "how many"
questions to prefer `aggregate_data` with `operation="count"`.

### REQ-9.2: Automatic Session Title Generation

**GIVEN** new chat sessions start with a generic title
**WHEN** the first user message is sent in a new session
**THEN** `generate_session_title()` must create a title from the message text, truncated at
the last word boundary within 50 characters, with an ellipsis appended if truncated. The
title must be saved to the database and pushed to the frontend.

### REQ-9.3: Title Update WebSocket Message

**GIVEN** the session title is generated after the first message
**WHEN** the title is saved
**THEN** a `title_updated` WebSocket message must be sent with `session_id` and `title`
fields, allowing the frontend sidebar to update in real-time without polling.

### REQ-9.4: Frontend Title Update Handling

**GIVEN** the frontend receives `title_updated` WebSocket messages
**WHEN** the ChatPage component processes messages
**THEN** the session list in the sidebar must update the matching session's title
immediately, without requiring a page refresh or API call.

### REQ-9.5: First-Message-Only Title Generation

**GIVEN** titles should only be auto-generated once per session
**WHEN** subsequent messages are sent after the first
**THEN** the `_maybe_update_title()` function must check `is_first_message` and skip
title generation for all subsequent messages.

### REQ-9.6: Word-Boundary Truncation

**GIVEN** session titles must fit in limited UI space
**WHEN** the first message exceeds 50 characters
**THEN** truncation must occur at the last space before the 50-character mark, falling back
to hard truncation if the message contains no spaces. An ellipsis (`...`) must be appended
to indicate truncation.

## Implementation Summary

### Files Created/Modified

- `src/knowledge_workers/llm/chat_agent.py` — Enhanced `SYSTEM_PROMPT` with detailed tool
  selection guide, filter syntax examples, workflow instructions
- `src/knowledge_api/routers/websocket_handler.py` — Added `generate_session_title()`,
  `_maybe_update_title()`, title auto-generation on first message
- `frontend/src/pages/ChatPage.tsx` — Handle `title_updated` WebSocket messages
- `frontend/src/lib/types.ts` — Extended `WebSocketMessage` type with `title_updated`
- `tests/unit/test_websocket_handler.py` — 8 tests for title generation
- `tests/unit/test_chat_agent.py` — Added 6 tests for system prompt content verification

### Key Patterns & Decisions

- `is_new_session` and `is_first_message` flags track state to auto-title only once
- Title truncation at word boundaries uses `rfind(" ")` with a fallback for single words
- `aggregate_entities` doesn't support a `filters` param — system prompt guides LLM to use
  `query_data` for filtered aggregations instead
- WebSocket message types extended with `title_updated` to keep the frontend in sync

## Discoveries

- `aggregate_entities` doesn't support filters — the system prompt must explicitly guide the
  LLM to use `query_data` for filtered aggregations
- Title truncation with `rfind(" ")` needs a `> 0` check to handle single-word messages
  that exceed the max length
- The `is_first_message` flag must account for sessions with pre-existing history (e.g.,
  resuming a session) — set to `True` only when `is_new_session and len(history) == 0`

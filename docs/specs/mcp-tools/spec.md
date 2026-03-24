# MCP Tools — Specification

**Phase**: 7
**Status**: Implemented (retroactive spec)
**Change**: mcp-tools

## Intent

Expose the knowledge app's key operations as MCP (Model Context Protocol) tools, enabling
any MCP-compatible client (Claude Desktop, GPT, etc.) to search, retrieve, and add knowledge
directly through conversation. Uses the `fastapi-mcp` library to auto-generate MCP tools
from existing FastAPI endpoints.

## Key Requirements

### REQ-7.1: MCP Server Mount

**GIVEN** the FastAPI application has existing API endpoints
**WHEN** the app factory creates the application
**THEN** a `FastApiMCP` instance must be created and mounted at `/mcp` using
`mount_http()` for streamable HTTP transport.

### REQ-7.2: Selective Operation Exposure

**GIVEN** the API has many endpoints but not all should be MCP tools
**WHEN** configuring the MCP server
**THEN** only four operations must be exposed as tools via `include_operations`:
- `search_knowledge` — Full-text search across entities (from `GET /api/graph/search`)
- `add_knowledge` — Add a new entity from text (from `POST /api/graph/knowledge`)
- `get_entity` — Retrieve a specific entity (from `GET /api/graph/entities/{id}`)
- `get_document_entities` — List entities from a document (from `GET /api/documents/{id}/entities`)

### REQ-7.3: Operation IDs on Endpoints

**GIVEN** fastapi-mcp identifies endpoints by their `operation_id`
**WHEN** defining API router endpoints
**THEN** all four exposed endpoints must have explicit `operation_id` parameters matching
the `MCP_TOOL_OPERATIONS` list.

### REQ-7.4: Graceful Degradation

**GIVEN** `fastapi-mcp` is an optional dependency
**WHEN** the library is not installed
**THEN** the MCP mount must catch the import error and log a warning without preventing
the application from starting.

### REQ-7.5: MCP Route Before SPA Catch-All

**GIVEN** the SPA catch-all route (`/{path:path}`) would intercept `/mcp`
**WHEN** routes are registered
**THEN** MCP must be mounted before the frontend catch-all to ensure `/mcp` requests
reach the MCP server.

## Implementation Summary

### Files Created/Modified

- `src/knowledge_api/app.py` — `_mount_mcp()` function, `MCP_TOOL_OPERATIONS` list
- `src/knowledge_api/routers/documents_router.py` — Added `operation_id` to endpoints
- `src/knowledge_api/routers/graph_router.py` — Added `operation_id` to endpoints
- `tests/unit/test_mcp.py` — 5 tests (operations list, route exists, POST support, ordering,
  OpenAPI schema)

### Key Patterns & Decisions

- Uses `fastapi-mcp` library rather than a hand-rolled MCP server — automatically derives
  tool schemas from OpenAPI/Pydantic definitions
- Only 4 of the ~21 total routes are exposed as MCP tools (read-heavy operations)
- The `_mount_mcp()` function is called after `_register_routers()` but before
  `_mount_frontend()` to ensure proper route ordering

## Discoveries

- `fastapi-mcp` uses `operation_id` from FastAPI route definitions to match tools — every
  endpoint exposed via MCP must have an explicit `operation_id` parameter
- The MCP mount creates a `POST /mcp` route for the streamable HTTP transport protocol
- Route ordering matters: MCP must be registered before the SPA catch-all or the catch-all
  will intercept `/mcp` requests and serve `index.html`

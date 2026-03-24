# REST API Layer — Specification

**Phase**: 5
**Status**: Implemented (retroactive spec)
**Change**: api-layer

## Intent

Build the complete REST API layer — Pydantic schemas, a dependency injection container,
four routers (documents, graph, chat, websocket), and an updated app factory with lifespan
management, CORS, MCP stub, and SPA serving. This is the inbound adapter layer connecting
HTTP/WebSocket requests to domain services.

## Key Requirements

### REQ-5.1: Pydantic Schemas

**GIVEN** domain entities exist in `knowledge_core`
**WHEN** API responses need serialization
**THEN** separate Pydantic models must exist for: `DocumentUploadResponse`,
`DocumentResponse`, `DocumentListResponse`, `UrlUploadRequest` (documents);
`EntityResponse`, `EntitySearchResponse`, `RelationshipResponse`,
`KnowledgeAddRequest` (graph); `ChatSessionCreate`, `ChatSessionUpdate`,
`ChatSessionResponse`, `ChatMessageResponse` (chat). Domain `StrEnum` fields must be
serialized as plain `str` in response schemas to decouple the API format.

### REQ-5.2: DI Container

**GIVEN** the application needs adapters wired together at startup
**WHEN** the application lifespan begins
**THEN** a `Container` singleton must wire: `AsyncEngine`, `async_sessionmaker`,
`DatabaseRepository`, `KeycloakAuthAdapter`, `LLMClient`, `ChatAgent`,
`FileDocumentStorage`, and `IngestionPipeline`. The container must have `initialize()`
and `shutdown()` async methods called during the FastAPI lifespan.

### REQ-5.3: Documents Router

**GIVEN** authenticated users want to manage documents
**WHEN** requests hit `/api/documents`
**THEN** the router must support: `POST /` (file upload with background processing via
`asyncio.create_task`), `POST /url` (URL ingestion), `GET /` (list user's documents),
`GET /{id}` (single document), `GET /{id}/entities` (entities from a document).
All endpoints must require Bearer token auth.

### REQ-5.4: Graph Router

**GIVEN** authenticated users want to query the knowledge graph
**WHEN** requests hit `/api/graph`
**THEN** the router must support: `GET /search` (full-text entity search with optional
type filter and limit), `GET /entities/{id}` (single entity),
`GET /entities/{id}/relationships` (entity relationships), `POST /knowledge`
(add knowledge from text via LLM extraction). All endpoints must require auth.

### REQ-5.5: Chat Router

**GIVEN** authenticated users want to manage chat sessions
**WHEN** requests hit `/api/chat`
**THEN** the router must support: `POST /sessions` (create), `GET /sessions` (list user's),
`GET /sessions/{id}` (single), `PATCH /sessions/{id}` (update title),
`DELETE /sessions/{id}` (delete), `GET /sessions/{id}/messages` (message history).
All endpoints must require auth.

### REQ-5.6: WebSocket Chat Handler

**GIVEN** real-time chat requires persistent connections
**WHEN** a client connects to `/ws/chat`
**THEN** the WebSocket handler must: authenticate via query param token, create or resume
a session (via optional `session_id` query param), send session info and history on connect,
then loop receiving user messages, running them through `ChatAgent`, persisting both user
and assistant messages, and sending responses back as JSON.

### REQ-5.7: Background Document Processing

**GIVEN** file uploads should return immediately
**WHEN** a document is uploaded via `POST /api/documents`
**THEN** the endpoint must save the document record, return the response, and kick off
`IngestionPipeline.process_existing_document()` via `asyncio.create_task()` for background
processing.

### REQ-5.8: App Factory Configuration

**GIVEN** the FastAPI application needs full configuration
**WHEN** `create_app()` is called
**THEN** it must: configure CORS from settings, register all routers under `/api` prefix
(except WebSocket which has no prefix), mount MCP at `/mcp`, mount the frontend SPA
with static assets and catch-all fallback, and register a `/health` endpoint.

### REQ-5.9: SPA Frontend Serving

**GIVEN** the built React frontend exists at `frontend/dist/`
**WHEN** a request doesn't match any API route
**THEN** the app must serve static files from the dist directory, with a catch-all route
returning `index.html` for client-side routing. The frontend directory must be resolved
from both `__file__`-relative and `cwd`-relative paths.

## Implementation Summary

### Files Created/Modified

- `src/knowledge_api/schemas/document_schemas.py` — Document request/response schemas
- `src/knowledge_api/schemas/entity_schemas.py` — Entity/relationship schemas
- `src/knowledge_api/schemas/chat_schemas.py` — Chat session/message schemas
- `src/knowledge_api/schemas/__init__.py` — Package init
- `src/knowledge_api/dependencies/container.py` — DI container wiring all adapters
- `src/knowledge_api/routers/documents_router.py` — Document CRUD + upload endpoints
- `src/knowledge_api/routers/graph_router.py` — Entity search + knowledge endpoints
- `src/knowledge_api/routers/chat_router.py` — Chat session management endpoints
- `src/knowledge_api/routers/websocket_handler.py` — WebSocket chat handler
- `src/knowledge_api/routers/__init__.py` — Package init
- `src/knowledge_api/app.py` — Updated app factory with lifespan, CORS, routers, MCP, SPA
- `src/knowledge_workers/ingestion/pipeline.py` — Added `process_existing_document()`
- `tests/unit/test_api_endpoints.py` — 20 tests for auth enforcement and container init

### Key Patterns & Decisions

- Document upload uses `asyncio.create_task` for background pipeline processing
- Domain models use `StrEnum` for status fields; API schemas use plain `str` to decouple
- Container type annotations use `noqa: TCH001/TCH002` for runtime type hints
- `SIM105` rule applied: `contextlib.suppress` over `try/except/pass` in WebSocket handler
- 21 routes registered total: 14 REST + 1 WS + 4 docs + health + openapi

## Discoveries

- The `settings.toml` has a pre-existing dynaconf format string issue
  (`LITE_LLM_PROXY_API_URL|https`) that prevents `LLMClient` initialization without proper
  `.env` — not caused by this phase, fixed in Phase 6
- `operation_id` is required on all endpoints exposed via MCP (fastapi-mcp uses it to
  identify tools)

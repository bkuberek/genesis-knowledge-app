# Knowledge Graph Application -- Initial Build Prompt

Build a web application called "Knowledge." Users upload documents (PDF, CSV, DOCX, TXT, or URLs), the system extracts entities and relationships using LLM-powered pipelines, stores everything in PostgreSQL, and lets users query their knowledge through a conversational chat interface. The application also exposes an MCP server so external AI assistants (Claude, GPT) can access the same knowledge graph tools, a REST API, and a CLI. Authentication is handled by Keycloak. The whole thing runs via Docker Compose. See `docs/product/user-requirements/` for the original assignment brief (PDF) and the sample dataset (CSV) that inspired this project -- we are taking those initial requirements much further to build a generic multi-user knowledge management tool.

The sample dataset is a CSV of 500 fictional SaaS companies with columns: company_name, industry_vertical, founding_year, arr_thousands, employee_count, churn_rate_percent, yoy_growth_rate_percent. The chatbot must be able to answer questions like "What's the average ARR for fintech companies?", "Which company has the highest growth rate?", "Show me companies founded after 2020 with less than 5% churn", and "How many companies have more than 100 employees?" These require structured property queries against real data, not just entity name search.

---

## Architecture Decisions

Use **hexagonal architecture** (ports and adapters). The core domain package (`core`) must have ZERO framework dependencies -- no FastAPI, no SQLAlchemy, no LiteLLM imports. It contains domain entities, abstract port interfaces (ABCs), application services, and exceptions. Everything else is an adapter.

Follow the **one class per file** convention strictly. `document.py` contains `Document`, `user.py` contains `User`, and so on.

The project is organized as **three Python packages** under `src/`:

- `core` -- domain entities, ports (inbound and outbound), application services, exceptions. Framework-independent.
- `api` -- inbound adapter: FastAPI REST endpoints, WebSocket chat handler, Keycloak auth middleware, DI container, MCP server mount, static file serving for the frontend.
- `workers` -- outbound adapters and processing: document ingestion pipeline, file parsers, LLM client (LiteLLM wrapper), entity extraction prompts, entity resolution, PostgreSQL repository implementations.

Ports are split into inbound (use case interfaces: `DocumentIngestionPort`, `KnowledgeQueryPort`, `ChatPort`) and outbound (infrastructure interfaces: `DatabaseRepositoryPort`, `DocumentStoragePort`, `LLMPort`, `AuthPort`). Core services depend on port abstractions via constructor injection. The DI container lives in the `api` package's `dependencies/` module and wires everything at startup via FastAPI lifespan.

Use async/await throughout -- async FastAPI endpoints, async SQLAlchemy (asyncpg), async LLM calls. Use Pydantic models for all data structures.

---

## Tech Stack

**Backend:** Python 3.12+, managed by `uv` (not pip/poetry). Use `src/` layout with `[tool.setuptools.packages.find] where = ["src"]`. FastAPI for the web framework with the app factory pattern (`create_app()` function for `uvicorn --factory`). cyclopts for CLI. Pydantic for data validation.

**Database:** PostgreSQL 16. Single database handles everything -- entities, documents, relationships, chat sessions, and Keycloak persistence (separate database on the same server). Use **SQLAlchemy async** with the **asyncpg** driver. JSONB columns for dynamic entity properties so the LLM can store arbitrary key-value data extracted from documents. GIN indexes on JSONB columns for fast property queries. Native SQL operators like `(properties->>'arr_thousands')::float > 500` for structured queries. **Row-Level Security (RLS)** for access control instead of manually adding ownership predicates to every query. Built-in **full-text search** via `tsvector`/`tsquery` for entity and document search. Optional **pgvector** extension for future semantic/vector search (not required for v1).

**LLM:** LiteLLM as a unified interface. The default model is Claude Sonnet via Anthropic. Use different models for different stages -- a cheaper model (Haiku) for classification, a more capable one (Sonnet) for extraction and chat. All LLM calls go through a single `LLMClient` wrapper; never import provider SDKs directly.

**Auth:** Keycloak for OAuth2/OIDC. Two clients in the Keycloak realm: `knowledge-app` (confidential, for backend) and `knowledge-web` (public, PKCE, for frontend). The realm is called `knowledge`. Provide a `realm-export.json` for auto-import on Keycloak startup. Include a test user (`test@knowledge.local` / `test123`).

**Config:** dynaconf with `settings.toml` for defaults and `.env` for secrets. Share configuration via the `core` package or a small `config` module. All config keys use the `KNOWLEDGE_` prefix for env vars (e.g., `KNOWLEDGE_DATABASE__URI`, `KNOWLEDGE_LLM__MODEL`).

**MCP:** fastapi-mcp, which auto-generates MCP tools from FastAPI OpenAPI operation_ids. Expose exactly 4 tools: `search_knowledge`, `add_knowledge`, `get_entity`, `get_document_entities`. Use `include_operations` to filter.

**Frontend:** React 18 + TypeScript + Vite + TailwindCSS v4. Use `keycloak-js` for auth (PKCE flow). WebSocket for chat. react-markdown for rendering. No component library, no Redux -- keep it minimal. The frontend builds to `frontend/dist/` and FastAPI serves it as static files in production.

**Infrastructure:** Docker Compose with three services: PostgreSQL (shared by app and Keycloak, separate databases), Keycloak, and the application. Multi-stage Dockerfile: stage 1 builds frontend (node:20-alpine), stage 2 installs Python deps (uv sync), stage 3 is the slim runtime.

**Testing:** pytest with pytest-asyncio (asyncio_mode = "auto"). Target around 50 focused tests. Unit tests mock ports, no infrastructure. Integration tests run against real PostgreSQL.

**Linting:** ruff for both linting and formatting. Target Python 3.12. Line length 100. Enable rules: E, W, F, I, N, UP, B, SIM, TCH.

---

## Data Model

Six PostgreSQL tables:

**documents** -- id (UUID PK), filename, file_path, content_type, upload_date, status (queued/processing/complete/error), stage (1-5), source_type (file/url), owner_id (UUID), visibility (private/public, default private), error_message, timestamps.

**entities** -- id (UUID PK), name, canonical_name (normalized for dedup), type (string), properties (JSONB), source_count (integer), timestamps. GIN index on `properties`. Unique index on `(canonical_name, type)`. Full-text search via `tsvector` on `name`.

**relationships** -- id (UUID PK), source_entity_id (FK), target_entity_id (FK), relation_type (string), description, confidence (float), source_document_id (FK), extracted_at.

**entity_documents** -- entity_id (FK), document_id (FK), relationship (string). Composite PK. This join table links entities to source documents and enables ACL: an entity is visible if at least one source document is accessible to the requesting user.

**chat_sessions** -- id (UUID PK), owner_id (UUID), title, timestamps.

**chat_messages** -- id (UUID PK), session_id (FK), role (user/assistant/tool), content (text), tool_calls (JSONB, nullable), tool_call_id (nullable), created_at.

**Access control** is enforced via PostgreSQL Row-Level Security. Set `app.current_user_id` on each database session, and RLS policies filter rows so users only see their own private data plus public data. This keeps ACL out of application code entirely.

---

## Document Processing Pipeline

Five stages, run asynchronously via `asyncio.create_task` (no Celery for v1):

1. **Intake and Classification** -- validate file, assign UUID, store on filesystem at `data/documents/{uuid}/{filename}`, create document row, classify content type via LLM.
2. **Content Extraction** -- parse file using format-specific parsers: pdfplumber (PDF), python-docx (DOCX), pandas (CSV), plain read (TXT), trafilatura (URL). Preserve structure like column headers and table schemas.
3. **LLM Knowledge Extraction** -- chunk long documents (~2000 tokens with overlap), prompt the LLM to extract entities (name, type, properties as key-value pairs) and relationships (subject, predicate, object, description). For CSV data, column headers inform entity type and property name inference.
4. **Entity Resolution and Deduplication** -- three-layer matching: (a) canonical name normalization (lowercase, strip whitespace, standardize), (b) exact match on canonical_name + compatible type, (c) fuzzy match via string similarity (threshold ~0.85), (d) LLM-assisted disambiguation for ambiguous cases. Matched entities are merged (properties combined, source_count incremented); unmatched are created fresh.
5. **Database Insertion** -- batch upsert: INSERT entities ON CONFLICT (canonical_name, type) DO UPDATE (merge properties JSONB), INSERT relationships, INSERT entity_documents links. Update document status to complete.

If any stage fails, set document status to "error" with error details. Partial results are not committed -- use a database transaction.

---

## Chat Agent

The chat agent is a custom LLM-powered tool-calling loop -- approximately 50 lines, NO LangChain or similar frameworks. It works like this:

1. Receive user message via WebSocket
2. Send to LLM with tool definitions and conversation history
3. If LLM returns tool_calls, execute them against the database (via existing service methods), append tool results to messages, loop back to step 2
4. If LLM returns text content, return it as the final response with accumulated source citations
5. Safety limit: max 5 tool-call rounds per message

Available tools (3-4 focused tools): `describe_tables` (returns entity types and their JSONB property keys/types -- LLM should call this first), `query_data` (filter and sort entities by type and JSONB property values via parameterized SQL), `aggregate_data` (AVG/SUM/COUNT/MIN/MAX on numeric JSONB properties with optional GROUP BY), and `search_entities` (full-text search on entity names with optional type filter). Tools generate parameterized SQL against JSONB properties -- much simpler than building a graph query layer.

Conversation history is maintained per chat session. Messages are persisted to PostgreSQL (chat_messages table) so users can resume conversations across page reloads.

---

## API Layer

REST endpoints: document CRUD (`POST /documents`, `POST /documents/url`, `GET /documents`, `GET /documents/{id}`, `GET /documents/{id}/entities`), graph queries (`GET /graph/search?q=`, `GET /graph/entities/{id}`, `GET /graph/entities/{id}/relationships`, `POST /graph/knowledge`), chat session CRUD (`GET/POST /chat/sessions`, `PATCH/DELETE /chat/sessions/{id}`), and `GET /health` (unauthenticated).

WebSocket: `/ws/chat?token=<jwt>&session_id=<uuid>` -- authenticated chat with tool-calling agent. Loads conversation history from the database on connect, appends new messages on each exchange.

All endpoints except `/health` and `/docs` require JWT authentication via `Depends(get_current_user)`. The DI container wires all services at startup via FastAPI lifespan. Set explicit `operation_id` on the 4 MCP-targeted endpoints so fastapi-mcp generates clean tool names. Mount the MCP server with `include_operations` filtering. Serve the frontend's `frontend/dist/` as static files -- the SPA catch-all route MUST be registered AFTER all API routes.

---

## Frontend

React SPA with Chat (primary, with session sidebar), Documents, and Search views. Keycloak OIDC login via `keycloak-js` with PKCE. Token stored in memory (not localStorage), passed as Bearer header on REST calls and as `?token=` query param on WebSocket connections. Chat renders markdown with source citations. File upload via drag-and-drop. Document list shows processing status. WebSocket manager handles reconnection with exponential backoff.

---

## Phased Delivery Plan

Build in this order. Each phase should be a separate commit (or small group of commits) with passing tests.

**Phase 1: Project Scaffold** -- Directory structure, three packages with stubs, `pyproject.toml`, `settings.toml`, `.env.example`, Docker Compose, Dockerfile, ruff/pytest config, `.gitignore`, smoke test. Verify `uv sync`, `ruff check`, `pytest`, `uvicorn --factory` all work.

**Phase 2: Database Layer + ACL** -- SQLAlchemy async models, Alembic migrations, connection pool, RLS policies, GIN indexes on JSONB, full-text search indexes, `DatabaseRepository` implementing `DatabaseRepositoryPort`. Integration tests.

**Phase 3: Document Ingestion Pipeline** -- All 5 parsers, `LLMClient` wrapper, extraction prompts, classification, chunking, entity resolution (3-layer), file storage adapter, pipeline orchestrator, `IngestionService`. Unit tests with mocked LLM.

**Phase 4: Authentication** -- `KeycloakAuthAdapter` (JWKS JWT validation), `get_current_user` dependency, WebSocket auth, realm export with two clients. Unit tests.

**Phase 5: REST API + WebSocket + DI** -- All REST endpoints, WebSocket chat handler, Pydantic schemas, DI container wiring, FastAPI lifespan.

**Phase 6: Chat Agent with Tool Calling** -- `chat_with_tools` in LLMPort/LLMClient, 3-4 tool schemas, agent loop (~50 lines), tool dispatch, source citations. Max 5 rounds.

**Phase 7: MCP Tools** -- operation_ids, `POST /graph/knowledge`, fastapi-mcp with `include_operations`. Verify 4 tools exposed.

**Phase 8: React Frontend** -- Vite + React + TypeScript, Keycloak OIDC, WebSocket chat with markdown, document upload/list, search, TailwindCSS v4, production build serving.

**Phase 9: Chat Session Persistence** -- Session/message storage in PostgreSQL, session CRUD endpoints, WebSocket loads history on connect, frontend session sidebar.

**Phase 10: Search and Query Refinement** -- Tune full-text search, optimize JSONB queries, validate the 4 example questions produce correct answers.

**Phase 11: Docker Full Stack + Integration Tests** -- `docker compose up` runs everything. End-to-end: upload CSV, process, ask question, get answer.

---

## GitHub Workflow

Set up CI with GitHub Actions:
- **On push to any branch:** run `ruff check src/ tests/` and `pytest` (quality gate)
- **On push to main:** version bump (semantic-release or similar), tag, changelog update

Use conventional commits: `feat:`, `fix:`, `docs:`, `chore:`. Always `ruff check` and `pytest` before committing. Pull before push to sync with any CI-generated version bumps. Semantic versioning is managed by the GitHub workflow on main. Work directly on main.

---

## Development Workflow

Use `uv` for all Python operations (`uv run pytest`, `uv run ruff check`, `uv run uvicorn`). Start infrastructure with `docker compose up -d`. Run the API with `uv run uvicorn knowledge_api.app:create_app --factory --reload`. Run the frontend with `cd frontend && npm run dev`.

### Spec-Driven Development (SDD)

For each substantial feature or change, follow the SDD workflow. Use the `/sdd-*` commands to drive each phase:

1. **`/sdd-explore <topic>`** -- Investigate the problem space, read relevant code, compare approaches, document findings
2. **`/sdd-propose <change-name>`** -- Write a proposal: intent, scope (in/out), approach, risks, success criteria. Save to `docs/specs/{change-name}/proposal.md`
3. **`/sdd-spec <change-name>`** -- Write a delta specification: requirements, acceptance criteria, GIVEN/WHEN/THEN scenarios, interface contracts. Save to `docs/specs/{change-name}/spec.md`
4. **`/sdd-design <change-name>`** -- Write a technical design: architecture decisions (ADR-style), component design, data flow, testing strategy. Save to `docs/specs/{change-name}/design.md`
5. **`/sdd-tasks <change-name>`** -- Break into implementation tasks with dependencies, parallelization opportunities, and batch groupings. Save to `docs/specs/{change-name}/tasks.md`
6. **`/sdd-apply <change-name>`** -- Implement in batches, delegating to sub-agents. Run tests after each batch.
7. **`/sdd-verify <change-name>`** -- Verify implementation against spec: check each acceptance criterion, run full test suite, report gaps.

Use `/sdd-ff <change-name>` to fast-forward through propose → spec → design → tasks in one go. Spec and design can run in parallel (both depend only on the proposal). Keep specs concise -- capture decisions and contracts, not prose. For small fixes and tweaks, skip SDD and just commit.

### Clean Code Principles

Apply clean code practices throughout. Use the clean code skills (`python-clean-code`, `clean-functions`, `clean-names`, `clean-comments`, `clean-tests`, `clean-general`, `boy-scout`) when writing, reviewing, or refactoring Python code:

- **Naming**: descriptive names at appropriate length, no abbreviations, no encodings. Names reveal intent.
- **Functions**: small (max ~20 lines), single responsibility, max 3 parameters, no boolean flag parameters. Extract till you drop.
- **Comments**: no redundant comments, no commented-out code, no metadata in comments. Code should be self-documenting. Only comment the "why" when the "what" isn't obvious.
- **DRY**: no duplication. Extract common logic. But don't abstract prematurely -- three similar lines are better than a premature helper.
- **Tests**: fast, independent, one assert per test concept, descriptive names (`test_<what>_<condition>_<expected>`), test boundary conditions.
- **Boy Scout Rule**: always leave code cleaner than you found it. If you touch a file, clean up what you see.

### Orchestrator Pattern

Delegate ALL implementation work to sub-agents. The orchestrator (main conversation) only coordinates, tracks state, and communicates with the user. Launch sub-agents in parallel where possible -- especially when interfaces are defined (e.g., backend and frontend can be built in parallel once API schemas are agreed). Define schemas and interfaces FIRST so parallel agents share the same contracts.

---

## Key Gotchas and Technical Pitfalls

**LiteLLM model format:** LiteLLM requires the provider prefix in model names: `anthropic/claude-sonnet-4-20250514`, not just `claude-sonnet-4-20250514`. Without the prefix, it cannot route to the correct provider.

**LiteLLM tool call arguments:** When the LLM returns tool calls, the `arguments` field may be a JSON string or a dict depending on the provider. Always handle both: `json.loads(args) if isinstance(args, str) else args`.

**`from __future__ import annotations` breaks FastAPI:** Do not use `from __future__ import annotations` in files that use FastAPI's `Depends()` with `TYPE_CHECKING` imports. FastAPI needs the actual type at runtime for dependency injection resolution, and deferred annotations make the types unavailable. Similarly, importing `uuid` or `AuthPort` under `TYPE_CHECKING` breaks path parameter resolution and dependency injection -- these need runtime imports (add `noqa: TCH003` to suppress ruff warnings).

**JWT audience verification:** Keycloak issues different `aud` claims per client (the backend gets `knowledge-app`, the frontend gets `knowledge-web`). Disable audience verification in the JWT validator, or your frontend tokens will be rejected by the backend. Validate issuer and signature instead.

**WebSocket authentication:** Browsers cannot set custom headers on WebSocket upgrade requests. Pass the JWT token as a query parameter: `ws://host/ws/chat?token=<jwt>`. Validate on connection before accepting.

**SPA catch-all route ordering:** FastAPI serves the React SPA's `index.html` for all non-API paths (client-side routing). This catch-all route MUST be registered AFTER all API routes, otherwise it will shadow them and API calls will return HTML.

**FastAPI Header(None) in newer versions:** Using `Header(None)` inside `Annotated` types causes assertion errors. Use `Header(default=None)` explicitly.

**TailwindCSS v4:** Uses the `@tailwindcss/vite` plugin -- no `tailwind.config.js` or `postcss.config.js` needed. Just install the plugin and import tailwind in your CSS with `@import "tailwindcss"`.

**keycloak-js modern browsers:** Set `checkLoginIframe: false` when initializing keycloak-js. The login iframe check causes issues in modern browsers with third-party cookie restrictions.

**Agent loop termination:** After hitting the max tool-call rounds, make one final LLM call with `tools=[]` (empty tools list) to force a text response rather than another tool call.

**JSONB property queries and SQL injection:** Entity properties are stored as JSONB, which means property access uses operators like `properties->>'key_name'`. Always use parameterized queries for values, and validate property names against the actual schema (introspected from the database) before interpolating them into column expressions. Never let user-supplied property names flow directly into SQL.

**SQLAlchemy async session lifecycle:** Always use `async with` for sessions. Do not hold sessions across await boundaries that yield to user code. Use `expire_on_commit=False` if you need to access attributes after commit without a new query.

**PostgreSQL RLS and connection pooling:** RLS policies check `current_setting('app.current_user_id')`. Set this at the start of each request using `SET LOCAL app.current_user_id = ...` inside a transaction. `SET LOCAL` scopes the setting to the current transaction, so it works correctly with connection pooling.

**Ruff TCH rules and FastAPI:** Ruff's TCH (type-checking) rules want you to move imports into `TYPE_CHECKING` blocks. This conflicts with FastAPI's runtime dependency resolution. Use `noqa: TCH` comments on the specific imports that FastAPI needs at runtime.

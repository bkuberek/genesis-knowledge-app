# Knowledge App

Multi-user knowledge management with LLM-powered entity extraction and conversational queries. Upload documents, automatically extract structured entities and relationships, then ask natural-language questions against your knowledge base.

## Quick Start

```bash
cp .env.example .env                        # Set KNOWLEDGE_LLM__API_KEY
docker compose up -d postgres keycloak      # Start infrastructure
uv sync --extra dev && uv run alembic upgrade head  # Install deps + migrate
uv run knowledge serve --reload             # API at localhost:8000
cd frontend && npm install && npm run dev   # Frontend at localhost:5173
```

Login with `test@knowledge.local` / `test123`. Full setup guide: [docs/getting-started.md](docs/getting-started.md).

**Stack:** Python 3.12, FastAPI, SQLAlchemy async, PostgreSQL 16, Keycloak 26, React 18, TypeScript, Vite, TailwindCSS v4, LiteLLM (Anthropic Claude).

## AI Tools Used and How

Claude (via LiteLLM proxy) powers entity extraction from documents, entity classification, and a conversational chat agent with tool-calling. The chat agent runs a custom tool-calling loop (~250 lines) that searches the knowledge base and composes answers from real data — no LangChain needed.

Built using **Spec-Driven Development (SDD)**: each feature went through explore, propose, spec, design, tasks, apply, verify. AI-assisted code generation with human-in-the-loop orchestration. SDD artifacts preserved in `docs/specs/`.

## Interesting Challenges

- **PostgreSQL RLS with FORCE semantics** — The app user owns tables, so `FORCE ROW LEVEL SECURITY` is required for policies to apply to the owner.
- **JSONB property queries with injection prevention** — Operator whitelist with parameterized values for safe dynamic property queries.
- **Custom tool-calling loop** — ~250 lines replace a heavy framework. The agent iterates tool calls until it has enough data to answer.
- **Keycloak 26 realm format** — `defaultRole` composite structure replaced the legacy `defaultRoles` array.
- **dynaconf @format limitations** — Switched to plain defaults with env var overrides.
- **WebSocket auth via query params** — Browsers can't set headers on WS upgrade; JWT passes as query parameter.

## What I'd Improve With More Time

- **pgvector** for semantic search alongside full-text search
- **Streaming responses** (SSE) for chat instead of full-message WebSocket
- **Integration tests** against real PostgreSQL + Keycloak
- Proper **entity visibility RLS** via entity_documents join (currently simplified)
- **Document chunking** with overlap for large files
- **Rate limiting** and request throttling
- Error notifications for background processing failures
- **End-to-end Playwright tests** for the frontend

## Design Decisions Worth Noting

- **Hexagonal architecture** — Core domain has zero framework dependencies. FastAPI, SQLAlchemy, LiteLLM are swappable adapters.
- **PostgreSQL does everything** — Entities, relationships, chat, search via JSONB + GIN indexes. No graph DB.
- **Custom chat agent** — ~50 lines of core logic for the tool-calling loop.
- **One class per file, constructor injection, async everywhere** — Predictable, testable patterns.
- **Background processing via asyncio.create_task** — No Celery for v1; status tracked in the database.

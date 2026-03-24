# Knowledge App

![CI](https://github.com/bkuberek/genesis-knowledge-app/actions/workflows/ci.yml/badge.svg) ![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg) ![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)

Multi-user knowledge management with LLM-powered entity extraction and conversational queries. Upload documents, extract structured entities and relationships, then ask natural-language questions against your knowledge base.

## Quick Start

```bash
cp .env.example .env                                # Set KNOWLEDGE_LLM__API_KEY
docker compose up -d postgres keycloak              # Start infrastructure
uv sync --extra dev && uv run alembic upgrade head  # Install deps + migrate
uv run knowledge serve --reload                     # API at localhost:8000
cd frontend && npm install && npm run dev           # Frontend at localhost:5173
```

Login with `test@knowledge.local` / `test123`. Full setup: [docs/getting-started.md](docs/getting-started.md).

**Stack:** Python 3.12, FastAPI, SQLAlchemy async, PostgreSQL 16, Keycloak 26, React 18, TypeScript, Vite, TailwindCSS v4, LiteLLM (Anthropic Claude).

## Interesting Challenges

- **OpenCode + LiteLLM proxy setup** -- Model names on the proxy don't match Anthropic's canonical names (`claude-sonnet-4-5` vs `anthropic/claude-sonnet-4-20250514`), causing 400 errors until we queried `/v1/models` to discover the correct identifiers.

- **Chat agent tool-calling reliability** -- The multi-round tool-calling loop surfaced several subtle bugs: LiteLLM expects `function.arguments` as a JSON string but the LLM returns a dict (crashing round two); tool results with UUIDs and datetimes aren't JSON-serializable by default; and JSONB property filters failed silently because the LLM sends numeric values as strings (`"2020"` vs `2020`), bypassing the numeric CAST path.

- **Entity extraction quality** -- Initially the entire 500-row CSV was sent to the LLM with a 4096 max_tokens limit, extracting only ~30-40 entities. The fix: CSVs are already structured data and don't need LLM interpretation. Direct parsing yields 100% accuracy. Case-sensitive string matching (`"fintech"` vs `"Fintech"`) required case-insensitive SQL comparisons.

- **Keycloak 26 in Docker** -- Health checks use port 9000 (management interface), not 8080. Environment variables changed from `KEYCLOAK_ADMIN` to `KC_BOOTSTRAP_ADMIN_USERNAME`. Token issuer mismatch between `localhost:8080` and `keycloak:8080` required a split URL configuration.

## Design Decisions

- **Hexagonal architecture** -- Domain logic has zero framework dependencies, making it testable and portable.
- **Direct CSV parsing** -- Structured data bypasses the LLM entirely; LLM is reserved for unstructured content (PDFs, text, URLs).
- **Defensive filter handling** -- Numeric string coercion + case-insensitive comparisons to handle LLM non-determinism.
- **Split Keycloak URL config** -- Separate issuer URL (for token validation) from JWKS URL (for key fetching) to handle Docker network DNS differences.
- **Session-scoped WebSocket** -- Each chat session gets its own WebSocket connection with automatic session creation on first message.

## What We'd Improve With More Time

- **Large dataset performance** -- Tested against a 500-row sample CSV; larger datasets (10K+ rows) expose bottlenecks in one-entity-per-row transactions and sequential scans on unindexed JSONB filters. Fixing this means batch inserts, GIN indexes on filtered JSONB paths, pagination, and materialized views for common aggregations.
- **Document sharing** -- Documents are user-scoped via Row-Level Security. Sharing would enable collaborative knowledge bases where teams query across pooled documents.
- **Graph database backend** -- A dedicated graph database (Neo4j or Apache AGE) would enable richer traversal queries awkward with relational JSONB joins.
- **Smarter ingestion** -- More document formats, chunked processing for large files, and LLM enrichment after direct parsing to infer entity relationships.
- **Real-time collaboration** -- WebSocket-based live updates when another user uploads or adds knowledge affecting shared entities.

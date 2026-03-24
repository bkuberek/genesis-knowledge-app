# Getting Started

A complete guide to setting up the Knowledge App for local development. By the end, you'll have the full stack running: PostgreSQL, Keycloak, the FastAPI backend, and the React frontend.

## Prerequisites

Install the following before you begin:

| Tool | Version | Install |
|------|---------|---------|
| **Python** | 3.12+ | [python.org](https://www.python.org/downloads/) |
| **uv** | latest | [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) |
| **Node.js** | 20+ | [nodejs.org](https://nodejs.org/) |
| **npm** | comes with Node.js | — |
| **Docker** | latest | [docker.com](https://www.docker.com/get-started/) |
| **Docker Compose** | v2+ (included with Docker Desktop) | — |
| **Git** | latest | [git-scm.com](https://git-scm.com/) |

Verify your installations:

```bash
python3 --version   # 3.12 or higher
uv --version        # any recent version
node --version      # 20 or higher
docker --version    # any recent version
docker compose version
git --version
```

## Clone and Setup

```bash
git clone <repo-url>
cd genesis-knowledge-app
```

## Environment Configuration

### Copy the example environment file

```bash
cp .env.example .env
```

### Environment variables reference

The application uses [dynaconf](https://www.dynaconf.com/) for configuration. Settings are loaded from two sources:

1. **`settings.toml`** — Default values checked into the repository. Organized by environment (`[default]`, `[development]`, `[production]`).
2. **`.env`** — Local overrides. Takes precedence over `settings.toml` for any variable it defines.

All environment variables use the `KNOWLEDGE_` prefix and double underscores (`__`) for nesting. For example, `KNOWLEDGE_DATABASE__HOST` maps to `settings.database.host` in Python.

| Variable | Default | Description |
|----------|---------|-------------|
| **`ENV_FOR_DYNACONF`** | `development` | Active environment. Controls which `[section]` in `settings.toml` is loaded. Use `development` locally, `production` in Docker. |
| **`KNOWLEDGE_DATABASE__HOST`** | `localhost` | PostgreSQL hostname. Matches `docker-compose.yml` default. |
| **`KNOWLEDGE_DATABASE__PORT`** | `5432` | PostgreSQL port. |
| **`KNOWLEDGE_DATABASE__NAME`** | `knowledge_db` | Main application database name. |
| **`KNOWLEDGE_DATABASE__USER`** | `knowledge` | PostgreSQL user. Matches the Docker Compose setup. |
| **`KNOWLEDGE_DATABASE__PASSWORD`** | `knowledge` | PostgreSQL password. |
| **`KNOWLEDGE_LLM__API_URL`** | `https://litellm-production-f079.up.railway.app` | LiteLLM proxy URL. Routes requests to the configured LLM provider (Anthropic). |
| **`KNOWLEDGE_LLM__API_KEY`** | *(empty)* | **You must set this.** Your API key for the LiteLLM proxy. Without it, entity extraction and chat will fail. |
| **`KNOWLEDGE_LLM__CHAT_MODEL`** | `anthropic/claude-sonnet-4-20250514` | Model used for the conversational chat agent. |
| **`KNOWLEDGE_LLM__EXTRACTION_MODEL`** | `anthropic/claude-sonnet-4-20250514` | Model used for entity extraction from documents. |
| **`KNOWLEDGE_LLM__CLASSIFICATION_MODEL`** | `anthropic/claude-haiku-4-20250414` | Model used for entity type classification. Haiku is faster and cheaper for this task. |
| **`LITE_LLM_PROXY_API_URL`** | same as `KNOWLEDGE_LLM__API_URL` | Legacy alias. Kept for backward compatibility. |
| **`LITE_LLM_PROXY_API_KEY`** | same as `KNOWLEDGE_LLM__API_KEY` | Legacy alias. |
| **`KNOWLEDGE_KEYCLOAK__SERVER_URL`** | `http://localhost:8080` | Keycloak server URL. |
| **`KNOWLEDGE_KEYCLOAK__REALM`** | `knowledge` | Keycloak realm name. Auto-imported from `docker/keycloak/realm-export.json`. |
| **`KNOWLEDGE_KEYCLOAK__CLIENT_ID`** | `knowledge-app` | OAuth2 confidential client ID for the backend API. |
| **`KNOWLEDGE_KEYCLOAK__CLIENT_SECRET`** | `knowledge-app-secret` | OAuth2 client secret. Matches the realm export. |
| **`KNOWLEDGE_STORAGE__DOCUMENT_PATH`** | `data/documents` | Local directory where uploaded documents are stored. |
| **`KNOWLEDGE_APP_NAME`** | `Knowledge` | Application display name. |
| **`KNOWLEDGE_DEBUG`** | `true` | Enable debug mode. Set to `false` in production. |

> **Important:** The only variable you _must_ change is `KNOWLEDGE_LLM__API_KEY`. Everything else works with defaults for local development.

## Start Infrastructure

The app requires PostgreSQL and Keycloak running as Docker containers:

```bash
docker compose up -d postgres keycloak
```

### What each service does

- **PostgreSQL 16** — The primary datastore. Hosts two databases:
  - `knowledge_db` — Application data (documents, entities, relationships, chat sessions)
  - `keycloak_db` — Keycloak's internal data (users, realms, sessions). Created automatically by `docker/postgres/init-keycloak-db.sql`.

- **Keycloak 26** — OAuth2/OIDC identity provider. Handles user registration, login, and JWT token issuance. Starts in dev mode with a pre-configured realm imported from `docker/keycloak/realm-export.json`.

### Verify services are running

```bash
# Check container status
docker compose ps

# PostgreSQL health (should show "healthy")
docker compose exec postgres pg_isready -U knowledge -d knowledge_db

# Keycloak admin console
# Open http://localhost:8080/admin in your browser
# Login with admin / admin
```

### Service ports

| Service | Port | URL |
|---------|------|-----|
| PostgreSQL | 5432 | `localhost:5432` |
| Keycloak | 8080 | [http://localhost:8080](http://localhost:8080) |
| Keycloak Admin | 8080 | [http://localhost:8080/admin](http://localhost:8080/admin) (admin / admin) |

### Verify Keycloak realm was imported

1. Open [http://localhost:8080/admin](http://localhost:8080/admin)
2. Log in with **admin** / **admin**
3. In the top-left dropdown, you should see the **knowledge** realm
4. Navigate to **Users** — you should see `test@knowledge.local`
5. Navigate to **Clients** — you should see `knowledge-app` (confidential) and `knowledge-web` (public PKCE)

> **Note:** Keycloak takes 30-60 seconds to fully start. The health check in `docker-compose.yml` has a `start_period: 60s` to account for this.

## Install Python Dependencies

```bash
uv sync --extra dev
```

This installs all project dependencies into a virtual environment managed by `uv`. The `--extra dev` flag includes development dependencies (pytest, ruff, httpx for testing).

**Why uv?** [uv](https://docs.astral.sh/uv/) is a fast Python package installer and resolver written in Rust. It replaces `pip` and `pip-tools` with dramatically faster dependency resolution and installation. If you're familiar with pip, the equivalent would be:

```bash
# Don't run this — use uv instead
pip install -e ".[dev]"
```

## Run Database Migrations

```bash
uv run alembic upgrade head
```

This applies the initial migration (`001_initial_schema`) which creates:

### Tables

| Table | Purpose |
|-------|---------|
| `documents` | Uploaded files with metadata, status tracking, and owner info |
| `entities` | Extracted entities with names, types, and JSONB properties |
| `relationships` | Directed edges between entities (source → target) with type and confidence |
| `entity_documents` | Join table linking entities to their source documents |
| `chat_sessions` | Per-user conversation sessions |
| `chat_messages` | Individual messages within chat sessions (user, assistant, tool calls) |

### Additional database objects

- **GIN index** on `entities.properties` — Fast JSONB queries
- **GIN index** on `entities.search_vector` — Full-text search
- **Unique index** on `(canonical_name, type)` — Entity deduplication
- **tsvector trigger** — Automatically updates `search_vector` when entity name changes
- **Row-Level Security (RLS)** policies on all tables — Each user can only see their own documents, entities (via document ownership), and chat sessions

### Verify the migration

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U knowledge -d knowledge_db

# List tables
\dt

# You should see:
#  documents
#  entities
#  relationships
#  entity_documents
#  chat_sessions
#  chat_messages
#  alembic_version

# Check RLS is enabled
\d documents
# Look for "Policies:" section

# Exit
\q
```

## Start the API Server

You have two options:

### Option A: Using uvicorn directly

```bash
uv run uvicorn knowledge_api.app:create_app --factory --reload --host 0.0.0.0 --port 8000
```

### Option B: Using the CLI

```bash
uv run knowledge serve --reload
```

Both commands do the same thing. The `--reload` flag enables auto-reload when you change Python source files.

### Verify the API is running

- **Swagger docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health check:** [http://localhost:8000/health](http://localhost:8000/health) — Should return `{"status": "healthy"}`

The API exposes these route groups:

| Prefix | Description |
|--------|-------------|
| `/api/documents` | Upload, list, and manage documents |
| `/api/graph` | Query entities, relationships, and properties |
| `/api/chat` | Chat sessions and message history |
| `/ws/chat` | WebSocket endpoint for real-time chat (session_id passed as optional query parameter) |
| `/mcp` | MCP (Model Context Protocol) tool server |
| `/health` | Health check endpoint |

## Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite development server starts at [http://localhost:5173](http://localhost:5173).

### Vite proxy configuration

The frontend dev server proxies API calls to the backend automatically (configured in `vite.config.ts`):

| Path | Target |
|------|--------|
| `/api/*` | `http://localhost:8000` |
| `/ws/*` | `ws://localhost:8000` (WebSocket) |

This means the frontend communicates with the backend at the same origin during development, avoiding CORS issues.

## Login and Test

1. Open [http://localhost:5173](http://localhost:5173) in your browser
2. You'll be redirected to the Keycloak login page
3. Log in with the pre-configured test user:
   - **Email:** `test@knowledge.local`
   - **Password:** `test123`
4. Alternatively, click **Register** to create a new account (self-registration is enabled in the realm)

After login, you'll be redirected back to the app.

## Upload Sample Data

1. Navigate to the **Documents** page
2. Click upload and select `docs/product/user-requirements/sample_data.csv`
3. Watch the document status progress:
   - **queued** — Waiting to be processed
   - **processing** (stages 1–5) — Parsing, entity extraction, classification, relationship extraction, resolution
   - **complete** — All entities and relationships extracted

Processing typically takes 30–60 seconds depending on document size and LLM response times.

### What happens during processing

The ingestion pipeline runs 5 stages:

1. **Parse** — Extract raw text from the file (CSV, PDF, DOCX, TXT, or URL)
2. **Extract entities** — LLM identifies entities (companies, people, metrics, etc.) with properties
3. **Classify entities** — LLM assigns canonical types to each entity
4. **Extract relationships** — LLM identifies connections between entities
5. **Resolve and store** — Deduplicate entities, merge properties, persist to database

## Ask Questions

Navigate to the **Chat** page and try conversational queries against your knowledge base:

1. *"What's the average ARR for fintech companies?"*
2. *"Which company has the highest growth rate?"*
3. *"Show me companies founded after 2020 with less than 5% churn"*
4. *"How many companies have more than 100 employees?"*

The chat agent uses tool-calling to search your knowledge base, query entity properties, and compose answers from real data.

## Running Tests

```bash
# All tests
uv run pytest -v

# Unit tests only
uv run pytest tests/unit/ -v

# Specific test file
uv run pytest tests/unit/test_chat_agent.py -v

# Lint check
uv run ruff check src/ tests/

# Format check
uv run ruff format --check src/ tests/

# Auto-format
uv run ruff format src/ tests/
```

The test suite includes unit tests for:
- Domain entities and ports
- API endpoints and health checks
- Authentication and WebSocket handling
- LLM client and chat agent
- Entity extraction and resolution
- Document parsers (CSV, PDF, DOCX, text)
- MCP tool integration

## Running with Docker (Full Stack)

To run the entire application (backend + frontend + infrastructure) in Docker:

```bash
docker compose up --build
```

This:
1. Starts PostgreSQL and Keycloak (with health checks)
2. Builds the app image using a multi-stage Dockerfile:
   - **Stage 1:** Builds the React frontend (`npm run build`)
   - **Stage 2:** Installs Python dependencies with `uv`
   - **Stage 3:** Creates a slim runtime image with both frontend and backend
3. Runs database migrations automatically via `docker/entrypoint.sh`
4. Starts the uvicorn server serving both the API and the frontend SPA

### Docker service ports

| Service | Port | URL |
|---------|------|-----|
| App (API + Frontend) | 8000 | [http://localhost:8000](http://localhost:8000) |
| Keycloak | 8080 | [http://localhost:8080](http://localhost:8080) |
| PostgreSQL | 5432 | `localhost:5432` |

> **Note:** In Docker mode, set `KNOWLEDGE_LLM__API_KEY` in your `.env` file before running `docker compose up`. The app container reads it via `env_file`.

## Project Structure

The application follows **hexagonal architecture** (ports & adapters) with a strict dependency rule: inner layers never depend on outer layers.

```
genesis-knowledge-app/
├── src/
│   ├── knowledge_core/           # Domain layer — ZERO framework dependencies
│   │   ├── domain/               # Entities: Document, Entity, Relationship, ChatSession, etc.
│   │   ├── ports/                # Abstract interfaces (ABCs) for repositories, auth, LLM
│   │   ├── services/             # Domain services (ingestion orchestration)
│   │   ├── config.py             # Dynaconf settings loader
│   │   └── exceptions.py         # Domain-specific exceptions
│   │
│   ├── knowledge_api/            # Inbound adapter — FastAPI
│   │   ├── app.py                # Application factory (CORS, lifespan, routing, MCP)
│   │   ├── cli.py                # CLI entrypoint (cyclopts)
│   │   ├── routers/              # HTTP endpoints: documents, graph, chat, WebSocket
│   │   ├── dependencies/         # DI container, auth middleware, WebSocket auth
│   │   ├── middleware/           # Request middleware
│   │   └── schemas/              # Pydantic request/response models
│   │
│   └── knowledge_workers/        # Outbound adapters
│       ├── adapters/             # PostgreSQL repository, document storage, Keycloak auth
│       │   └── models/           # SQLAlchemy ORM models
│       ├── llm/                  # LiteLLM client, chat agent with tool-calling loop
│       ├── ingestion/            # Entity extraction, classification, resolution pipeline
│       └── parsers/              # File parsers: CSV, PDF, DOCX, TXT, URL
│
├── frontend/                     # React 18 SPA
│   ├── src/
│   │   ├── pages/                # Route pages (Documents, Chat, Graph)
│   │   ├── components/           # Reusable UI components
│   │   └── lib/                  # Auth, API client, utilities
│   ├── vite.config.ts            # Dev server with API proxy
│   └── package.json
│
├── docker/                       # Infrastructure
│   ├── Dockerfile                # Multi-stage build (frontend + Python + runtime)
│   ├── entrypoint.sh             # Runs migrations then starts server
│   ├── keycloak/
│   │   └── realm-export.json     # Pre-configured Keycloak realm
│   └── postgres/
│       └── init-keycloak-db.sql  # Creates keycloak_db on first run
│
├── alembic/                      # Database migrations
│   ├── env.py                    # Async migration runner
│   └── versions/
│       └── 001_initial_schema.py # Tables, indexes, triggers, RLS policies
│
├── docs/                         # Documentation and specs
│   ├── getting-started.md        # This file
│   ├── product/                  # Product requirements and sample data
│   └── specs/                    # SDD artifacts (proposals, specs, designs, tasks)
│
├── tests/                        # Test suite
│   ├── unit/                     # Unit tests (14 test files)
│   └── integration/              # Integration test stubs
│
├── settings.toml                 # Default configuration (dynaconf)
├── .env.example                  # Environment variable template
├── pyproject.toml                # Python project metadata and dependencies
├── alembic.ini                   # Alembic configuration
├── docker-compose.yml            # Service orchestration
└── .github/workflows/ci.yml     # CI pipeline (lint, test, version)
```

## Common Issues and Troubleshooting

### Keycloak not starting

**Symptom:** Keycloak container restarts or stays "unhealthy."

**Fix:** Keycloak 26 takes 30–60 seconds to initialize on first run. Wait and check logs:

```bash
docker compose logs -f keycloak
```

If it keeps failing, increase the health check timing in `docker-compose.yml`:

```yaml
start_period: 120s  # increase from 60s
```

### Keycloak port 9000 conflict

**Symptom:** Keycloak health check fails, or another service on your machine conflicts with port 9000.

**Explanation:** Keycloak 26 uses port **9000** for its management interface and health checks (`/health/ready`), separate from the main HTTP port 8080. This is _not_ configurable via the standard `KC_HTTP_PORT` setting. The `docker-compose.yml` health check targets port 9000 internally — this port is not published to the host, so it won't conflict with host services. However, if you see health check failures, check that no Docker network policy is blocking internal port 9000.

```bash
# Verify Keycloak health inside the container
docker compose exec keycloak curl -sf http://localhost:9000/health/ready
# Expected: {"status":"UP","checks":[...]}
```

> **Note:** The management port (9000) is only used internally for health checks. Users and the application connect to Keycloak on port 8080.

### LLM errors during document processing or chat

**Symptom:** Documents stuck in "processing" or chat returns errors.

**Fix:** Verify your API key is set in `.env`:

```bash
grep KNOWLEDGE_LLM__API_KEY .env
# Should show your actual key, not "your-api-key-here"
```

### Database migration fails

**Symptom:** `alembic upgrade head` errors.

**Fix:** Ensure PostgreSQL is running and accessible:

```bash
docker compose ps postgres              # should show "healthy"
docker compose exec postgres pg_isready  # should say "accepting connections"
```

If the database was in a bad state, reset it:

```bash
docker compose down -v   # WARNING: destroys all data
docker compose up -d postgres keycloak
uv run alembic upgrade head
```

### Frontend can't connect to the backend

**Symptom:** Network errors in the browser console, 502 or connection refused.

**Fix:** Ensure the backend is running on port 8000:

```bash
curl http://localhost:8000/health
# Should return {"status":"healthy"}
```

Check that `vite.config.ts` proxy targets match:

```ts
proxy: {
  '/api': 'http://localhost:8000',
  '/ws': { target: 'ws://localhost:8000', ws: true },
}
```

### CORS errors

**Symptom:** Browser console shows "CORS policy" errors.

**Fix:** The backend allows `localhost:5173` (Vite dev) and `localhost:8000` by default. If you're running the frontend on a different port, update `ALLOWED_ORIGINS` in `src/knowledge_api/app.py`.

### WebSocket connection fails

**Symptom:** Chat doesn't receive responses, WebSocket errors in console.

**Fix:** WebSocket authentication uses a `token` query parameter (browsers can't set custom headers on WebSocket upgrade). Ensure the frontend is passing the JWT token in the WebSocket URL:

```
ws://localhost:8000/ws/chat?token={jwt_token}&session_id={optional_session_id}
```

### "Module not found" errors

**Symptom:** Python import errors when running the server.

**Fix:** Make sure you're using `uv run` (which activates the virtual environment) and that `src/` is in the Python path:

```bash
uv run python -c "import knowledge_api; print('OK')"
```

## MCP Integration

The application exposes an MCP (Model Context Protocol) server at `/mcp`, making its tools available to any MCP-compatible client (Claude Desktop, GPT, etc.).

### Available MCP tools

| Tool | Description |
|------|-------------|
| `search_knowledge` | Full-text search across entities |
| `add_knowledge` | Add a new entity to the knowledge base |
| `get_entity` | Retrieve a specific entity with all properties |
| `get_document_entities` | List all entities extracted from a document |

### Connect from Claude Desktop

Add the following to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "knowledge": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

After connecting, Claude can search your knowledge base, retrieve entity details, and add new knowledge directly through conversation.

## CI/CD Pipeline

The project uses GitHub Actions (`.github/workflows/ci.yml`) with three jobs:

1. **lint** — Runs `ruff check` and `ruff format --check` against Python 3.12
2. **test** — Runs `pytest` on Python 3.12 and 3.13 (matrix strategy)
3. **version** — On pushes to `main`, runs `python-semantic-release` to auto-bump the version based on conventional commit messages

Supported commit prefixes for versioning:
- `feat:` — Minor version bump
- `fix:`, `perf:` — Patch version bump
- `docs:`, `chore:`, `ci:`, `style:`, `refactor:`, `test:`, `build:` — No version bump

# Design: Project Scaffold (Phase 1)

## Technical Approach

Bootstrap a working Python monorepo with hexagonal architecture (three packages under `src/`), Docker-based infrastructure, configuration, CI/CD, and test scaffolding. All files are foundational stubs — no business logic. The app factory returns a FastAPI instance with a `/health` endpoint that passes a smoke test. Implements all 6 ADRs from the proposal.

## Architecture Decisions

| # | Decision | Choice | Alternatives Rejected | Rationale |
|---|----------|--------|----------------------|-----------|
| ADR-1 | Package structure | 3 packages under `src/` (knowledge_core, knowledge_api, knowledge_workers) | Flat module, single package | Hexagonal architecture enforces dependency direction; core has ZERO framework imports |
| ADR-2 | Package manager | `uv` with committed `uv.lock` | pip+requirements.txt, poetry | Fastest resolver, deterministic lock, built-in venv management. Must REMOVE `uv.lock` from `.gitignore` |
| ADR-3 | Configuration | dynaconf (settings.toml + .env) with `KNOWLEDGE_` prefix | pydantic-settings, python-dotenv | Layered config, nested `__` separator, environment switching built-in |
| ADR-4 | Docker stack | Compose with PostgreSQL 16 (2 DBs), Keycloak 26, app | Separate DB instances | Single Postgres reduces resource overhead; `initdb.d` script creates second DB |
| ADR-5 | Dockerfile | Multi-stage: node:20-alpine -> python:3.12-slim -> slim runtime | Single-stage, distroless | Frontend build isolated; final image minimal (~200MB vs ~1.5GB) |
| ADR-6 | CI/CD | GitHub Actions: quality.yml (push any branch), release.yml (push main) | GitLab CI, CircleCI | Native to GitHub; semantic-release automates versioning |

## Data Flow

```
                        +-------------+
                        |  Browser /  |
                        |  API Client |
                        +------+------+
                               |
                     +---------v---------+
                     |   knowledge_api   |
                     |  (FastAPI app)    |
                     |  /health -> 200   |
                     +---------+---------+
                               |
              +----------------+----------------+
              |                                 |
    +---------v---------+            +----------v----------+
    |  knowledge_core   |            | knowledge_workers   |
    |  (domain, config) |            | (adapters, outbound)|
    +-------------------+            +---------------------+
```

## File Layout

```
project-root/
  pyproject.toml            # Hatchling build, src-layout, all deps, ruff+pytest config
  settings.toml             # Dynaconf defaults: database, llm, keycloak, storage, app
  .env.example              # All KNOWLEDGE_* env vars with placeholder values
  alembic.ini               # Points to alembic/ directory
  docker-compose.yml        # postgres, keycloak, app services
  docker/
    Dockerfile              # Multi-stage: node -> python -> slim
    keycloak/
      realm-export.json     # Realm "knowledge", 2 clients, test user
    postgres/
      init-keycloak-db.sql  # CREATE DATABASE keycloak_db
  .github/
    workflows/
      ci.yml                # ruff + pytest on push
  src/
    knowledge_core/
      __init__.py           # Package version
      config.py             # Dynaconf settings singleton
      exceptions.py         # Base exception hierarchy
      domain/               # (empty, Phase 2)
      ports/                # (empty, Phase 2)
      services/             # (empty, Phase 2)
    knowledge_api/
      __init__.py
      app.py                # create_app() factory with /health endpoint
      cli.py                # cyclopts: serve, version commands
    knowledge_workers/
      __init__.py
  tests/
    __init__.py
    conftest.py             # Shared fixtures
    test_smoke.py           # Import tests + app factory test
  data/
    documents/
      .gitkeep
```

## Key Implementation Details

### pyproject.toml
- Build system: `hatchling` with `packages = ["src/knowledge_core", "src/knowledge_api", "src/knowledge_workers"]`
- Python requires: `>=3.12`
- Console script: `knowledge = "knowledge_api.cli:app"`
- Ruff: `target-version = "py312"`, `line-length = 100`, select = `["E", "W", "F", "I", "N", "UP", "B", "SIM", "TCH"]`
- Pytest: `asyncio_mode = "auto"`, `testpaths = ["tests"]`

### settings.toml
```toml
[default]
APP_NAME = "Knowledge"
DEBUG = false

[default.database]
host = "localhost"
port = 5432
name = "knowledge_db"
user = "knowledge"
password = "knowledge"

[default.llm]
api_url = ""
api_key = ""
chat_model = "anthropic/claude-sonnet-4-20250514"
extraction_model = "anthropic/claude-sonnet-4-20250514"
classification_model = "anthropic/claude-haiku-4-20250414"

[default.keycloak]
server_url = "http://localhost:8080"
realm = "knowledge"
client_id = "knowledge-app"
client_secret = ""

[default.storage]
document_path = "data/documents"

[development]
DEBUG = true
```

### Docker Compose
- `postgres`: PostgreSQL 16-alpine, healthcheck via `pg_isready`
- `keycloak`: Keycloak 26.0, `start-dev --import-realm`, depends on postgres healthy
- `app`: builds from `docker/Dockerfile`, depends on postgres+keycloak healthy

### create_app() Factory
```python
def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
```

---

*Generated via SDD (Spec-Driven Development) | Engram observation #61*

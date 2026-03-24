# Tasks: Project Scaffold (Phase 1)

> **Status**: All tasks complete (implemented in SDD apply phase)

## Batch 1: Foundation (must go first)

- [x] 1.1 Create `pyproject.toml` — setuptools build, src-layout, Python >=3.12, all runtime deps (fastapi, uvicorn[standard], sqlalchemy[asyncio], asyncpg, pydantic, dynaconf, cyclopts, alembic, python-jose[cryptography], httpx, litellm, python-multipart, pdfplumber, python-docx, pandas, trafilatura, aiofiles, websockets, fastapi-mcp), dev deps (pytest, pytest-asyncio, ruff, httpx). Configure ruff (line-length=100, rules E,W,F,I,N,UP,B,SIM,TCH), pytest (asyncio_mode=auto, testpaths=tests).
- [x] 1.2 Create `settings.toml` — `[default]`, `[development]`, and `[production]` environments, nested keys for database, llm, keycloak, storage config sections.
- [x] 1.3 Create `.env.example` — all `KNOWLEDGE_` env vars with placeholder values matching settings.toml keys. Kept existing `.env.sample` as-is.
- [x] 1.4 Update `.gitignore` — removed `uv.lock` entry, added `.atl/` for SDD internal directory. All existing entries preserved.
- [x] 1.5 Create `data/documents/.gitkeep` — document storage directory placeholder.
- [x] 1.6 **Verify**: `uv sync` exits 0, `uv.lock` created, `ruff --version` works.

## Batch 2: Source Packages + App + Tests + Alembic

### knowledge_core (no framework deps)
- [x] 2.1 Create `src/knowledge_core/__init__.py` with docstring and `__version__ = "0.1.0"`.
- [x] 2.2 Create `src/knowledge_core/config.py` — dynaconf `Dynaconf` instance loading `settings.toml` with `KNOWLEDGE_` prefix.
- [x] 2.3 Create `src/knowledge_core/exceptions.py` — base `KnowledgeError` and subclasses: `DocumentProcessingError`, `EntityResolutionError`, `AuthenticationError`, `AuthorizationError`.
- [x] 2.4 Create `src/knowledge_core/domain/__init__.py` (empty).
- [x] 2.5 Create `src/knowledge_core/ports/__init__.py` (empty).
- [x] 2.6 Create `src/knowledge_core/services/__init__.py` (empty).

### knowledge_api
- [x] 2.7 Create `src/knowledge_api/__init__.py` with docstring.
- [x] 2.8 Create `src/knowledge_api/app.py` — `create_app()` factory returning FastAPI with `/health` endpoint.
- [x] 2.9 Create `src/knowledge_api/cli.py` — cyclopts app with `serve` (uvicorn) and `version` commands.

### knowledge_workers
- [x] 2.10 Create `src/knowledge_workers/__init__.py` with docstring.

### Tests
- [x] 2.11 Create `tests/__init__.py` (empty).
- [x] 2.12 Create `tests/conftest.py` — shared fixtures (async client, event loop).
- [x] 2.13 Create `tests/test_smoke.py` — import all 3 packages, test `create_app()` returns FastAPI, test GET `/health` returns 200.

### Alembic
- [x] 2.14 Create `alembic.ini` — points to `alembic/` directory, uses async driver.
- [x] 2.15 Create `alembic/env.py` — async Alembic env loading DB URL from dynaconf.
- [x] 2.16 Create `alembic/versions/.gitkeep`.

## Batch 3: Docker + CI

- [x] 3.1 Create `docker/Dockerfile` — multi-stage (node:20-alpine, python:3.12-slim, slim runtime), non-root user.
- [x] 3.2 Create `docker-compose.yml` — postgres (16-alpine), keycloak (26.0), app services with healthchecks.
- [x] 3.3 Create `docker/keycloak/realm-export.json` — realm "knowledge", two clients, test user.
- [x] 3.4 Create `docker/postgres/init-keycloak-db.sql` — `CREATE DATABASE keycloak_db`.
- [x] 3.5 Create `.github/workflows/ci.yml` — ruff check + pytest on push.
- [x] 3.6 Create `.dockerignore` — exclude `.git`, `node_modules`, `__pycache__`, `.venv`, `data/`.
- [x] 3.7 **Verify**: `ruff check src/ tests/` passes, `pytest -v` passes.

---

*Generated via SDD (Spec-Driven Development) | Engram observation #62*

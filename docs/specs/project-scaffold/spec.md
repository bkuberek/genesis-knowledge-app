# Specification: Project Scaffold (Phase 1)

## Purpose

Define the verifiable requirements for bootstrapping the genesis-knowledge-app from greenfield to a buildable, lintable, testable, containerizable Python monorepo.

---

## Domain: Project Structure

### Requirement: Source Layout

The repository MUST use a `src/` layout containing three Python packages: `knowledge_core`, `knowledge_api`, `knowledge_workers`. Each package MUST have an `__init__.py` file.

#### Scenario: Package discovery

- GIVEN fresh clone of the repository
- WHEN listing `src/knowledge_core/`, `src/knowledge_api/`, `src/knowledge_workers/`
- THEN each directory exists and contains `__init__.py`

### Requirement: Data Directory

The repository MUST include `data/documents/.gitkeep` for local document storage.

#### Scenario: Data dir exists

- GIVEN fresh clone
- WHEN listing `data/documents/`
- THEN `.gitkeep` exists

---

## Domain: Dependency Management

### Requirement: pyproject.toml Configuration

`pyproject.toml` MUST define the project with src-layout, Python >=3.12, all runtime dependencies (fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, pydantic, pydantic-settings, dynaconf, cyclopts, alembic, python-jose, httpx, litellm, python-multipart, jinja2), and dev dependencies (pytest, pytest-asyncio, ruff, pre-commit). Build system MUST be hatchling with `src/` source path.

#### Scenario: Dependency install

- GIVEN fresh clone
- WHEN running `uv sync`
- THEN all dependencies install with exit code 0

### Requirement: Lock File Committed

`uv.lock` MUST NOT be in `.gitignore`. The lock file MUST be committed for reproducible builds.

#### Scenario: Lock file tracked

- GIVEN the repository
- WHEN checking `git check-ignore uv.lock`
- THEN the command returns non-zero (file is NOT ignored)

---

## Domain: Configuration

### Requirement: Dynaconf Settings

`settings.toml` MUST exist at project root with `[default]` and `[development]` environments. All settings MUST use `KNOWLEDGE_` prefix for env var override. Settings MUST include nested sections for: database (host, port, name, user, password), llm (api_url, api_key, chat_model, extraction_model, classification_model), keycloak (server_url, realm, client_id, client_secret), storage (document_path), and app (app_name, debug).

#### Scenario: Settings load

- GIVEN `settings.toml` exists and ENV_FOR_DYNACONF=development
- WHEN importing `knowledge_core.config.settings`
- THEN `settings.DATABASE.HOST` returns `"localhost"` and `settings.APP_NAME` returns `"Knowledge"`

### Requirement: Env Example

`.env.example` MUST contain all `KNOWLEDGE_*` env var names with safe placeholder values. Developers MUST be able to copy it to `.env` and have a working local setup (with docker-compose defaults).

#### Scenario: Copy-and-go

- GIVEN developer copies `.env.example` to `.env`
- WHEN starting `docker compose up` and then the API
- THEN application starts successfully (database and auth connect)

---

## Domain: Docker Infrastructure

### Requirement: Docker Compose Stack

`docker-compose.yml` MUST define services: `postgres` (PostgreSQL 16), `keycloak` (Keycloak 26), `app` (application). PostgreSQL MUST serve both the app database and Keycloak database. Health checks MUST be configured for postgres and keycloak.

#### Scenario: Stack starts

- GIVEN fresh clone with `.env` configured
- WHEN running `docker compose up -d postgres keycloak`
- THEN both services reach healthy state within 60s

### Requirement: Keycloak Realm Import

`docker/keycloak/realm-export.json` MUST configure a realm named `knowledge` with:
- Self-registration enabled (`registrationAllowed: true`, `registrationEmailAsUsername: true`)
- SSL not required for development (`sslRequired: "none"`)
- Two clients: `knowledge-app` (confidential, service accounts) and `knowledge-web` (public, PKCE S256)
- A test user (`test@knowledge.local` / `test123`)
- Default role `user` assigned to new registrations

#### Scenario: Realm imports successfully

- GIVEN docker compose starts keycloak with `--import-realm`
- WHEN keycloak reaches healthy state
- THEN the `knowledge` realm exists with both clients and the test user

### Requirement: Dockerfile

Multi-stage `Dockerfile` MUST include: Stage 1 (node:20-alpine for frontend build), Stage 2 (python:3.12-slim for dependency install), Stage 3 (slim runtime). MUST use non-root user for runtime.

#### Scenario: Docker build succeeds

- GIVEN repository root
- WHEN running `docker build -f docker/Dockerfile .`
- THEN build completes with exit code 0

---

## Domain: Code Quality

### Requirement: Ruff Configuration

`pyproject.toml` MUST configure ruff with: target-version = "py312", line-length = 100, rules E, W, F, I, N, UP, B, SIM, TCH. Format quote-style MUST be "double".

#### Scenario: Lint passes

- GIVEN all source files exist
- WHEN running `uv run ruff check src/ tests/`
- THEN exit code 0 (no violations)

### Requirement: Pytest Configuration

`pyproject.toml` MUST configure pytest with asyncio_mode = "auto" and testpaths = ["tests"].

#### Scenario: Smoke tests pass

- GIVEN all packages exist with stubs
- WHEN running `uv run pytest -v`
- THEN all tests pass, including: import of all 3 packages, app factory creates FastAPI instance, health endpoint returns 200

---

## Domain: CI/CD

### Requirement: Quality Workflow

`.github/workflows/ci.yml` MUST run on push to any branch: checkout, setup Python 3.12, install uv, sync deps, run ruff check, run pytest.

#### Scenario: CI passes on clean code

- GIVEN all code passes lint and tests locally
- WHEN pushing to any branch
- THEN GitHub Actions quality job passes

---

## Domain: Application Stubs

### Requirement: App Factory

`src/knowledge_api/app.py` MUST export `create_app()` that returns a `FastAPI` instance with a `/health` endpoint returning `{"status": "ok"}`.

#### Scenario: Health check

- GIVEN app created via `create_app()`
- WHEN GET `/health`
- THEN response is 200 with body `{"status": "ok"}`

### Requirement: CLI Entry Point

`src/knowledge_api/cli.py` MUST define a cyclopts-based CLI with at least `serve` and `version` commands. `pyproject.toml` MUST register `knowledge` as a console script pointing to the CLI.

#### Scenario: CLI version

- GIVEN package installed
- WHEN running `uv run knowledge version`
- THEN prints the version string

### Requirement: Config Module

`src/knowledge_core/config.py` MUST export a `settings` object (Dynaconf instance) that loads from `settings.toml` with `KNOWLEDGE_` env prefix.

#### Scenario: Config import

- GIVEN `settings.toml` exists
- WHEN `from knowledge_core.config import settings`
- THEN settings object is a Dynaconf instance with expected keys

---

*Generated via SDD (Spec-Driven Development) | Engram observation #60*

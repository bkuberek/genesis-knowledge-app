# Docker Polish — Specification

**Phase**: 11
**Status**: Implemented (retroactive spec)
**Change**: docker-polish

## Intent

Polish the Docker setup for full-stack production deployment — fix the Dockerfile build
pipeline, add database migration entrypoint, configure docker-compose for production with
proper health checks, env_file support, and Keycloak split-URL configuration.

## Key Requirements

### REQ-11.1: Multi-Stage Dockerfile

**GIVEN** the application has both a Node.js frontend and Python backend
**WHEN** building the Docker image
**THEN** a 3-stage Dockerfile must: (1) build the React frontend with `node:20-alpine`,
(2) install Python dependencies with `python:3.12-slim` and `uv sync --frozen --no-dev
--no-editable`, (3) create a slim runtime image copying the venv, source code, config
files, frontend build, and entrypoint script. The `src/` directory must be present at
build time because `pyproject.toml` uses `setuptools` with `where = ["src"]`.

### REQ-11.2: Entrypoint with Migrations

**GIVEN** database migrations must run before the server starts
**WHEN** the container starts
**THEN** `entrypoint.sh` must: wait for PostgreSQL to accept connections (TCP socket check
with 30 retries), run `alembic upgrade head`, then start uvicorn. Migration failures must
log a warning but not prevent startup.

### REQ-11.3: PostgreSQL Readiness Check

**GIVEN** `python:3.12-slim` doesn't include `pg_isready`
**WHEN** the entrypoint waits for PostgreSQL
**THEN** a Python socket connection check must be used instead of `pg_isready`, with
configurable host/port from `KNOWLEDGE_DATABASE__HOST` and `KNOWLEDGE_DATABASE__PORT`
environment variables.

### REQ-11.4: Docker Compose Production Config

**GIVEN** the full stack needs to run in Docker
**WHEN** configuring `docker-compose.yml`
**THEN** the app service must: use `env_file` with `required: false` (Docker Compose 2.17+)
to avoid failure when `.env` doesn't exist, set production environment variables for
database, Keycloak (with split URLs: `SERVER_URL` for internal, `ISSUER_URL` for external),
and LLM configuration with env var cascading.

### REQ-11.5: Keycloak Health Check

**GIVEN** Keycloak 26 uses port 9000 for the management interface
**WHEN** Docker Compose checks Keycloak health
**THEN** the health check must use a TCP connection to port 9000 with an HTTP request to
`/health/ready`, grepping for `'UP'` in the response body (Keycloak returns JSON
`{"status":"UP"}`).

### REQ-11.6: Frontend Path Resolution

**GIVEN** non-editable installs change the `__file__` path resolution
**WHEN** the app tries to serve the frontend SPA
**THEN** `_resolve_frontend_dir()` must check multiple candidate paths: both
`__file__`-relative and `cwd`-relative, returning the first directory that exists.

### REQ-11.7: .dockerignore

**GIVEN** Docker builds should exclude unnecessary files
**WHEN** building the Docker image
**THEN** `.dockerignore` must exclude: `.git`, `.venv`, `node_modules`, `__pycache__`,
`tests/`, `docs/`, `.env` files (except `.env.example`), IDE files, markdown files,
and `docker-compose.yml`.

### REQ-11.8: Service Dependencies

**GIVEN** services must start in the correct order
**WHEN** Docker Compose starts the stack
**THEN** Keycloak must depend on PostgreSQL (`service_healthy`), and the app must depend on
both PostgreSQL and Keycloak (`service_healthy`). All services must use
`restart: unless-stopped`.

## Implementation Summary

### Files Created/Modified

- `docker/Dockerfile` — 3-stage build (node frontend → python deps → slim runtime)
- `docker/entrypoint.sh` — PostgreSQL wait + alembic migrations + uvicorn start
- `docker-compose.yml` — env_file with required:false, restart:unless-stopped, Keycloak
  health check on port 9000, split Keycloak URL configuration
- `.dockerignore` — Excludes git, venv, node_modules, tests, docs, env files
- `src/knowledge_api/app.py` — `_resolve_frontend_dir()` with multiple path candidates

### Key Patterns & Decisions

- `uv sync --frozen --no-dev --no-editable` requires `src/` present at build time because
  `pyproject.toml` uses setuptools with `where = ["src"]`
- Keycloak split URLs: `KEYCLOAK__SERVER_URL` for internal container communication,
  `KEYCLOAK__ISSUER_URL` for JWT `iss` claim validation (browser-visible URL)
- TCP socket check in Python used instead of `pg_isready` (not available in slim image)
- `env_file: [{path: .env, required: false}]` syntax requires Docker Compose 2.17+

## Discoveries

- `pyproject.toml` uses setuptools with `where = ["src"]`, so `uv sync --no-editable`
  needs the `src/` directory present at build time
- Keycloak 26 `/health/ready` returns JSON with `"status":"UP"`, not `"200 OK"` in the
  body — health check must grep for `'UP'`
- `python:3.12-slim` doesn't have `pg_isready`, so TCP socket check is the portable
  alternative
- Docker Compose 2.17+ supports `env_file: [{path: .env, required: false}]` to avoid
  failure when `.env` doesn't exist
- `alembic.ini` has `prepend_sys_path = src` which ensures alembic can find the
  `knowledge_core` and `knowledge_workers` packages in the container

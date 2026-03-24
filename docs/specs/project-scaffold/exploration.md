# Project Scaffold — Exploration

## Exploration: Phase 1 — Project Scaffold

### Current State

The project is greenfield. The repository contains only:
- `.gitignore` (already has Python, Node, uv, IDE, data, coverage entries)
- `.env` / `.env.sample` (LiteLLM proxy credentials only)
- `CLAUDE.md` (SDD orchestrator config)
- `docs/product/initial-user-prompt.md` (full engineering brief)
- `docs/product/initial-user-prompt-v2.md` (condensed brief)
- `docs/product/user-requirements/` (original assignment PDF + sample_data.csv)
- Config files: `opencode.json`, `skills-lock.json`, `.agents/`, `.atl/`, `.claude/`

No Python code, no pyproject.toml, no Docker files, no settings, no tests exist yet.

**Environment**: Python 3.13.12, uv 0.10.11, Docker 29.1.3, Docker Compose v5.0.1 are all available locally.

### Affected Areas (files to create)

All files below are NEW — nothing to modify except `.gitignore` and `.env.sample`.

#### Root config files
- `pyproject.toml` — project metadata, dependencies, tool config (ruff, pytest)
- `settings.toml` — dynaconf defaults (database, LLM, auth, app settings)
- `.env.example` — template for secrets (rename from `.env.sample` or augment)
- `Dockerfile` — multi-stage (frontend + Python runtime)
- `docker-compose.yml` — PostgreSQL 16, Keycloak, app services
- `keycloak/realm-export.json` — auto-import realm config
- `.github/workflows/ci.yml` — ruff + pytest on push, semantic versioning on main

#### Source packages
- `src/knowledge_core/__init__.py` — domain package stub
- `src/knowledge_core/config.py` — dynaconf settings singleton
- `src/knowledge_api/__init__.py` — API package stub
- `src/knowledge_api/app.py` — app factory (`create_app()`)
- `src/knowledge_api/cli.py` — cyclopts CLI entry point
- `src/knowledge_workers/__init__.py` — workers package stub

#### Tests
- `tests/__init__.py`
- `tests/conftest.py` — shared fixtures
- `tests/test_smoke.py` — import tests + basic app factory test

#### Data directory
- `data/documents/.gitkeep` — document storage directory placeholder

### Key Decisions Required

1. **Build backend**: `hatchling` vs `setuptools` — both work with src-layout, hatchling is lighter
2. **Keycloak version**: 24 (proposal) vs 26 (latest stable) — should match docker image
3. **Docker base image**: `python:3.12-slim` vs `python:3.13-slim` — 3.12 for broader compatibility
4. **CI matrix**: Python 3.12 only, or 3.12+3.13 — single version keeps CI simple at this stage

### Risks & Considerations

- `.env.sample` already exists with LiteLLM creds — need to preserve those in `.env.example`
- `uv.lock` is currently in `.gitignore` — must remove that entry per spec
- Keycloak realm import needs careful JSON structure — broken realm config blocks local dev
- Multi-stage Dockerfile with frontend build stage will be a no-op until frontend exists

---

*Generated via SDD (Spec-Driven Development) | Engram observation #57*

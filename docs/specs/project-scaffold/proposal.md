# Project Scaffold — Proposal

# Proposal: Project Scaffold (Phase 1)

## Intent

Bootstrap the genesis-knowledge-app repository from a greenfield state to a fully buildable, lintable, testable, and containerizable Python monorepo. This foundation enables all subsequent phases (domain modeling, ingestion, LLM, API, frontend) to start from a consistent, working baseline.

## Scope

### In Scope
1. **Python monorepo** — `pyproject.toml` (uv, src-layout), three packages: `knowledge_core`, `knowledge_api`, `knowledge_workers`
2. **Dependencies** — all known deps pinned by major version; dev deps for testing/linting
3. **Configuration** — `settings.toml` (dynaconf defaults, KNOWLEDGE_ prefix) + `.env.example` (secrets template)
4. **Docker stack** — `docker-compose.yml` (PostgreSQL 16, Keycloak 24, app service), multi-stage `Dockerfile` (Node frontend build -> uv deps -> slim runtime)
5. **Keycloak** — `keycloak/realm-export.json` (realm "knowledge", confidential + public PKCE clients, self-registration, test user)
6. **Linting** — ruff config (Python 3.12, line-length 100, rules E,W,F,I,N,UP,B,SIM,TCH)
7. **Testing** — pytest config (asyncio_mode=auto), smoke test importing all packages + app factory
8. **CI/CD** — `.github/workflows/ci.yml` (ruff + pytest on push), release workflow (semantic versioning on main)
9. **Package stubs** — `__init__.py` per package, `app.py` (create_app factory), `cli.py` (cyclopts entry point), `config.py` (dynaconf settings)
10. **Alembic skeleton** — `alembic.ini` + `alembic/env.py` + `alembic/versions/` (no migrations yet)
11. **Data dir** — `data/documents/.gitkeep`
12. **Project docs** — update `CLAUDE.md` with commands/conventions, update `.gitignore`

### Out of Scope
- Domain entities, ports, application services (Phase 2)
- Database models or actual migrations (Phase 2)
- LLM integration or ingestion pipeline (Phase 3)
- API endpoints (Phase 5)
- Frontend code (Phase 8)

## Approach

Single-batch creation — all files are foundational and have no code interdependencies, so they can be created in one pass. Order within batch: root configs -> packages -> tests -> Docker -> CI.

## Architecture Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| ADR-1 | Package structure | 3 packages under `src/` | Hexagonal architecture: core (domain), api (inbound), workers (outbound) |
| ADR-2 | Package manager | `uv` with committed lock file | Fast, deterministic, already installed |
| ADR-3 | Config | dynaconf with `KNOWLEDGE_` prefix | Layered config, env override, built-in env switching |
| ADR-4 | Docker | Compose with shared Postgres | Single DB instance, separate databases via init script |
| ADR-5 | Dockerfile | Multi-stage (node + python) | Frontend build isolated, slim runtime image |
| ADR-6 | CI | GitHub Actions (quality + release) | Native to GitHub, semantic-release for versioning |

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Keycloak realm JSON invalid | Medium | Export from running instance, validate on startup |
| Dependency conflicts | Low | uv resolver catches early; lock file committed |
| Docker build slow | Low | Multi-stage caching, .dockerignore |

---

*Generated via SDD (Spec-Driven Development) | Engram observation #59*

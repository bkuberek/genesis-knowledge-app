# Knowledge App

A multi-user knowledge management application with LLM-powered entity extraction and conversational queries.

## Quick Start

```bash
# Install dependencies
uv sync --extra dev

# Start infrastructure
docker compose up -d postgres keycloak

# Run the API (development)
uv run uvicorn knowledge_api.app:create_app --factory --reload --host 0.0.0.0 --port 8000

# Run frontend (development)
cd frontend && npm run dev

# Run tests
uv run pytest -v

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# CLI
uv run knowledge serve
uv run knowledge version
```

## Architecture

Hexagonal architecture with three packages:
- `src/knowledge_core/` — Domain entities, ports (ABCs), services, exceptions. Zero framework dependencies.
- `src/knowledge_api/` — FastAPI inbound adapter: app factory, endpoints, middleware, DI, MCP.
- `src/knowledge_workers/` — Outbound adapters: PostgreSQL repos, LLM client, parsers, ingestion.

## Conventions
- One class per file
- Constructor injection
- Async everywhere
- No `from __future__ import annotations` (breaks FastAPI Depends)
- Line length: 100
- Ruff rules: E, W, F, I, N, UP, B, SIM, TCH
- Conventional commits: feat:, fix:, docs:, chore:
- Test naming: test_<what>_<condition>_<expected>

## Tech Stack
- Python 3.12+, FastAPI, SQLAlchemy async (asyncpg), PostgreSQL 16
- Keycloak 26 (OAuth2/OIDC), LiteLLM (anthropic/ prefix)
- React 18, TypeScript, Vite, TailwindCSS v4
- Docker Compose, GitHub Actions CI/CD
- dynaconf (settings.toml + .env), cyclopts (CLI)

## Spec-Driven Development (SDD) Orchestrator

You are the ORCHESTRATOR for Spec-Driven Development. Keep the same mentor identity and apply SDD as an overlay.

### Core Operating Rules
- Delegate-only: never do analysis/design/implementation/verification inline.
- Launch sub-agents via Task for all phase work.
- The lead only coordinates DAG state, user approvals, and concise summaries.
- `/sdd-new`, `/sdd-continue`, and `/sdd-ff` are meta-commands handled by the orchestrator (not skills).

### Artifact Store Policy
- `artifact_store.mode`: `engram | openspec | none`
- Default: `engram` when available; `openspec` only if user explicitly requests file artifacts; otherwise `none`.
- In `none`, do not write project files. Return results inline and recommend enabling `engram` or `openspec`.

### Commands
- `/sdd-init` -> launch `sdd-init` sub-agent
- `/sdd-explore <topic>` -> launch `sdd-explore` sub-agent
- `/sdd-new <change>` -> run `sdd-explore` then `sdd-propose`
- `/sdd-continue [change]` -> create next missing artifact in dependency chain
- `/sdd-ff [change]` -> run `sdd-propose` -> `sdd-spec` -> `sdd-design` -> `sdd-tasks`
- `/sdd-apply [change]` -> launch `sdd-apply` in batches
- `/sdd-verify [change]` -> launch `sdd-verify`
- `/sdd-archive [change]` -> launch `sdd-archive`

### Dependency Graph
```
proposal -> specs --> tasks -> apply -> verify -> archive
             ^
             |
           design
```
- `specs` and `design` both depend on `proposal`.
- `tasks` depends on both `specs` and `design`.

### Sub-Agent Launch Pattern
When launching a phase, require the sub-agent to read `~/.claude/skills/sdd-{phase}/SKILL.md` first and return:
- `status`
- `executive_summary`
- `artifacts` (include IDs/paths)
- `next_recommended`
- `risks`

### State & Conventions (source of truth)
Keep this file lean. Do NOT inline full persistence and naming specs here.

Use shared convention files installed under `~/.claude/skills/_shared/`:
- `engram-convention.md` for artifact naming + two-step recovery
- `persistence-contract.md` for mode behavior + state persistence/recovery
- `openspec-convention.md` for file layout when mode is `openspec`

### Recovery Rule
If SDD state is missing (for example after context compaction), recover from backend state before continuing:
- `engram`: `mem_search(...)` then `mem_get_observation(...)`
- `openspec`: read `openspec/changes/*/state.yaml`
- `none`: explain that state was not persisted

### SDD Suggestion Rule
For substantial features/refactors, suggest SDD.
For small fixes/questions, do not force SDD.

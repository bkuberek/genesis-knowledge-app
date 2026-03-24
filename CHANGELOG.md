# CHANGELOG

All notable changes to this project will be documented in this file.

This file is auto-maintained by [python-semantic-release](https://python-semantic-release.readthedocs.io/).

## v1.3.6 (2026-03-24)

### Bug Fixes

- correct DB_HOST default to postgres, remove stale KC_DB vars
  ([`5084c2c`](https://github.com/bkuberek/genesis-knowledge-app/commit/5084c2c))

## v1.3.5 (2026-03-24)

### Bug Fixes

- unify database credentials across all services
  ([`57e9af6`](https://github.com/bkuberek/genesis-knowledge-app/commit/57e9af6))

## v1.3.4 (2026-03-24)

### Bug Fixes

- bind volumes to /mnt/data/ for persistent storage on homelab
  ([`1bcf3bb`](https://github.com/bkuberek/genesis-knowledge-app/commit/1bcf3bb))

## v1.3.3 (2026-03-24)

### Bug Fixes

- prevent Coolify timeout by relaxing Keycloak dependency
  ([`32509ef`](https://github.com/bkuberek/genesis-knowledge-app/commit/32509ef))

## v1.3.2 (2026-03-24)

### Bug Fixes

- resolve Keycloak startup failures on Coolify deployment
  ([`b1973d1`](https://github.com/bkuberek/genesis-knowledge-app/commit/b1973d1))

## v1.3.1 (2026-03-24)

### Bug Fixes

- add dedicated PostgreSQL to production compose
  ([`765ec98`](https://github.com/bkuberek/genesis-knowledge-app/commit/765ec98))

## v1.3.0 (2026-03-24)

### Features

- add Coolify production deployment for genesis-knowledge-demo.kuberek.org
  ([`1e326ec`](https://github.com/bkuberek/genesis-knowledge-app/commit/1e326ec))

### Documentation

- add CI, Python, and Ruff badges to README
  ([`fa02bf7`](https://github.com/bkuberek/genesis-knowledge-app/commit/fa02bf7))

## v1.2.0 (2026-03-24)

### Features

- polish Docker stack with entrypoint, healthchecks, and build fixes
  ([`0d5b549`](https://github.com/bkuberek/genesis-knowledge-app/commit/0d5b549))

### Documentation

- add README and comprehensive getting-started guide
  ([`bb53209`](https://github.com/bkuberek/genesis-knowledge-app/commit/bb53209))

## v1.1.0 (2026-03-24)

### Features

- add Keycloak JWT authentication with WebSocket support
  ([`e8a4350`](https://github.com/bkuberek/genesis-knowledge-app/commit/e8a4350))

- add document ingestion pipeline with LLM extraction and entity resolution
  ([`c9003a3`](https://github.com/bkuberek/genesis-knowledge-app/commit/c9003a3))

- add REST API endpoints, WebSocket handler, DI container, and schemas
  ([`0229ba0`](https://github.com/bkuberek/genesis-knowledge-app/commit/0229ba0))

- add chat agent with tool-calling loop and fix settings config
  ([`2ce1756`](https://github.com/bkuberek/genesis-knowledge-app/commit/2ce1756))

- mount MCP server exposing 4 knowledge tools via fastapi-mcp
  ([`c2eb505`](https://github.com/bkuberek/genesis-knowledge-app/commit/c2eb505))

- add React frontend with Keycloak OIDC, WebSocket chat, and document upload
  ([`acdb885`](https://github.com/bkuberek/genesis-knowledge-app/commit/acdb885))

- enhance chat agent prompt and add session auto-titling
  ([`6b90bbf`](https://github.com/bkuberek/genesis-knowledge-app/commit/6b90bbf))

### Bug Fixes

- consolidate CI into single workflow with gated versioning
  ([`6be6c5d`](https://github.com/bkuberek/genesis-knowledge-app/commit/6be6c5d))

- update Keycloak realm for KC26 format and complete .env.example
  ([`f54ec96`](https://github.com/bkuberek/genesis-knowledge-app/commit/f54ec96))

### Documentation

- persist SDD specs to docs/specs/ for team review
  ([`9480918`](https://github.com/bkuberek/genesis-knowledge-app/commit/9480918))

## v1.0.0 (2026-03-24)

### Features

- add domain entities, port interfaces, and unit tests
  ([`1ff10d5`](https://github.com/bkuberek/genesis-knowledge-app/commit/1ff10d5))

- add SQLAlchemy models, database infrastructure, and initial migration
  ([`29f3e4d`](https://github.com/bkuberek/genesis-knowledge-app/commit/29f3e4d))

- implement DatabaseRepository with JSONB queries, FTS, and upsert
  ([`3710dd6`](https://github.com/bkuberek/genesis-knowledge-app/commit/3710dd6))

### Bug Fixes

- update GitHub Actions workflows to match mkcv reference patterns
  ([`275b8e8`](https://github.com/bkuberek/genesis-knowledge-app/commit/275b8e8))

## v0.1.0 (2026-03-24)

### Features

- scaffold project with hexagonal architecture, Docker, and CI/CD
  ([`449c186`](https://github.com/bkuberek/genesis-knowledge-app/commit/449c186))

  - Three Python packages: knowledge_core, knowledge_api, knowledge_workers
  - pyproject.toml with uv, src/ layout, 19 runtime + 4 dev dependencies
  - FastAPI app factory with /health endpoint, cyclopts CLI
  - dynaconf config (settings.toml + .env.example) with KNOWLEDGE_ prefix
  - Docker Compose: PostgreSQL 16, Keycloak 26, app service
  - Multi-stage Dockerfile (node frontend + python deps + runtime)
  - Keycloak realm-export.json with 2 OAuth2 clients and test user
  - GitHub Actions: quality (ruff + pytest) and release (semantic-release)
  - Alembic async migration skeleton
  - 6 passing tests (smoke imports + health endpoint)
  - ruff configured: Python 3.12, line-length 100, rules E/W/F/I/N/UP/B/SIM/TCH

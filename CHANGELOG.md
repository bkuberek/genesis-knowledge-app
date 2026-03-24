# CHANGELOG


## v0.1.0 (2026-03-24)

### Chores

- Add agent skills
  ([`579feb2`](https://github.com/bkuberek/genesis-knowledge-app/commit/579feb28585057320dd66b7b19482e3b8f433e91))

- Add claude.md with initial instructions
  ([`b7470cc`](https://github.com/bkuberek/genesis-knowledge-app/commit/b7470ccef4701de6ca7ecf9c14f1a05d5b609ac5))

- Add opencode.json
  ([`d1b9881`](https://github.com/bkuberek/genesis-knowledge-app/commit/d1b9881b7d4da9fd49b1eeb38c9705673f4372b3))

- Remove opencode.json add sample instead
  ([`c250997`](https://github.com/bkuberek/genesis-knowledge-app/commit/c250997cb384e785772e82bb3f5c1c44cf0612e0))

### Features

- Scaffold project with hexagonal architecture, Docker, and CI/CD
  ([`449c186`](https://github.com/bkuberek/genesis-knowledge-app/commit/449c186c331a91196b699db54e25a18b73fc7d05))

- Three Python packages: knowledge_core, knowledge_api, knowledge_workers - pyproject.toml with uv,
  src/ layout, 19 runtime + 4 dev dependencies - FastAPI app factory with /health endpoint, cyclopts
  CLI - dynaconf config (settings.toml + .env.example) with KNOWLEDGE_ prefix - Docker Compose:
  PostgreSQL 16, Keycloak 26, app service - Multi-stage Dockerfile (node frontend + python deps +
  runtime) - Keycloak realm-export.json with 2 OAuth2 clients and test user - GitHub Actions:
  quality (ruff + pytest) and release (semantic-release) - Alembic async migration skeleton - 6
  passing tests (smoke imports + health endpoint) - ruff configured: Python 3.12, line-length 100,
  rules E/W/F/I/N/UP/B/SIM/TCH

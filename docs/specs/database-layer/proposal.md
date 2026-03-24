# Proposal: Database Layer + ACL

## Intent

Implement the complete PostgreSQL data layer for the Knowledge App — domain entities, port interfaces, SQLAlchemy async models, Alembic migration with RLS policies, and repository adapters. This is the foundational persistence layer (Phase 2) that all subsequent phases (ingestion, auth, API, chat) depend on.

## Scope

### In Scope
- **Domain entities** (7 classes): Document, Entity, Relationship, EntityDocument, ChatSession, ChatMessage, User (JWT-only, no DB table)
- **Port interfaces** (2 ABCs): DocumentRepositoryPort (CRUD all persisted entities), DocumentStoragePort (file I/O)
- **SQLAlchemy async models** (6 files): one model per file in `knowledge_workers/adapters/`, JSONB+GIN indexes, tsvector FTS on `entities.name`, proper FKs and cascades
- **Alembic initial migration**: all 6 tables, RLS policies (documents by owner_id, entities via entity_documents join), GIN index on `entities.properties`, unique index on `(canonical_name, type)`
- **DB connection management**: async engine + session factory, session middleware setting `app.current_user_id` for RLS
- **Repository implementation**: `DatabaseRepository` implementing port, all async, parameterized queries, safe JSONB queries

### Out of Scope
- REST API endpoints (Phase 5)
- Document processing pipeline (Phase 3)
- Authentication middleware (Phase 4)
- Chat agent logic (Phase 6)

## Approach

Bottom-up, dependency-ordered implementation:

1. **Domain entities first** — pure Pydantic models in `knowledge_core/domain/`, zero framework deps
2. **Port interfaces** — ABCs in `knowledge_core/ports/` defining repository and storage contracts
3. **SQLAlchemy models** — ORM mappings in `knowledge_workers/adapters/models/`, one file per table
4. **Alembic migration** — single initial migration creating all tables, indexes, RLS policies
5. **Connection management** — async engine factory + scoped session in `knowledge_workers/adapters/database.py`
6. **Repository adapter** — `DatabaseRepository` in `knowledge_workers/adapters/` implementing all port methods

## Architecture Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| ADR-1 | Domain entity base | Pydantic BaseModel | Keeps knowledge_core zero-framework; Pydantic gives validation+serialization |
| ADR-2 | ORM style | SQLAlchemy 2.0 DeclarativeBase + Mapped[T] | Type-safe columns, auto DDL for Alembic |
| ADR-3 | Dynamic properties | JSONB column + GIN index | Single column, fast containment queries |
| ADR-4 | Access control | PostgreSQL RLS policies | Enforced at DB level, can't leak rows from raw queries |
| ADR-5 | Text search | tsvector + trigger + GIN index | Native PG, zero infra, safe user input |
| ADR-6 | Session management | async_sessionmaker + per-request context | Matches FastAPI async pattern |

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| RLS complexity | Medium | Test with multiple user contexts; document policy SQL |
| JSONB query performance | Low | GIN index + containment operator |
| Migration conflicts | Low | Single initial migration; team coordination |

---

*Generated via SDD (Spec-Driven Development) | Engram observation #66*

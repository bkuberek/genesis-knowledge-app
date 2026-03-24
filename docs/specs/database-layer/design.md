# Design: Database Layer + ACL

## Technical Approach

Bottom-up implementation of PostgreSQL persistence: pure Pydantic domain entities -> ABC port interfaces -> SQLAlchemy 2.0 async models -> Alembic migration with RLS -> repository adapter. Follows the project's hexagonal architecture — `knowledge_core` stays framework-free, all ORM lives in `knowledge_workers`.

## Architecture Decisions

| # | Decision | Choice | Alternatives Rejected | Rationale |
|---|----------|--------|-----------------------|-----------|
| ADR-1 | Domain entity base | Pydantic `BaseModel` | SQLAlchemy mapped dataclasses, attrs | Keeps `knowledge_core` zero-framework; Pydantic gives validation+serialization for free; matches existing `config.py` pattern |
| ADR-2 | ORM style | SQLAlchemy 2.0 `DeclarativeBase` + `Mapped[T]` | Classical mapper, raw asyncpg | Type-safe columns, auto-generates DDL for Alembic, already in pyproject deps |
| ADR-3 | Dynamic properties | JSONB column + GIN index | EAV table, separate property tables | Single column, fast `@>` containment queries, no schema migration for new property keys |
| ADR-4 | Access control | PostgreSQL RLS policies | Application-level WHERE filters | Enforced at DB level — can't leak rows even from raw queries or future tools; `SET LOCAL` scoped to transaction |
| ADR-5 | Text search | `tsvector` column + trigger + GIN index | Elasticsearch, pg_trgm LIKE | Native PG, zero infra, `plainto_tsquery` handles user input safely, `ts_rank` for relevance |
| ADR-6 | Session management | `async_sessionmaker` + per-request context manager | Scoped sessions, manual engine.connect | Matches FastAPI async pattern, `expire_on_commit=False` avoids lazy-load issues |

## Data Flow

```
Request -> FastAPI middleware
         |
         v
  get_session(user_id)
         |  SET LOCAL app.current_user_id = :uid
         v
  Repository method (async session)
         |  SQLAlchemy ORM query
         v
  PostgreSQL (RLS filters rows)
         |
         v
  Return domain objects
```

## File Layout

```
src/knowledge_core/
  domain/
    __init__.py              # Re-exports all entities
    document.py              # Document + enums (R1)
    entity.py                # Entity (R2)
    relationship.py          # Relationship (R3)
    entity_document.py       # EntityDocument (R4)
    chat_session.py          # ChatSession (R5)
    chat_message.py          # ChatMessage + MessageRole (R6)
    user.py                  # User, JWT-only (R7)
  ports/
    __init__.py              # Re-exports ports
    database_repository_port.py  # DatabaseRepositoryPort ABC (R8)
    document_storage_port.py     # DocumentStoragePort ABC (R9)

src/knowledge_workers/
  adapters/
    __init__.py
    models/
      __init__.py            # Re-exports all models
      base.py                # Base(DeclarativeBase), TimestampMixin
      document_model.py      # DocumentModel (R10)
      entity_model.py        # EntityModel + JSONB + tsvector (R11)
      relationship_model.py  # RelationshipModel (R12)
      entity_document_model.py  # EntityDocumentModel (R13)
      chat_session_model.py  # ChatSessionModel (R14)
      chat_message_model.py  # ChatMessageModel (R15)
    database.py              # Engine factory + session manager (R16, R17)
    database_repository.py   # DatabaseRepository (R19)

alembic/
  versions/
    001_initial_schema.py    # All tables, indexes, RLS (R18)
```

## Key Implementation Details

### Domain Entities (knowledge_core)
- All entities use `pydantic.BaseModel` with `model_config = ConfigDict(from_attributes=True)` for ORM compatibility
- UUIDs use `uuid.uuid4` as default factory
- Datetimes use `datetime.utcnow` as default factory
- Enums extend `StrEnum` for JSON serialization

### SQLAlchemy Models (knowledge_workers)
- `Base(DeclarativeBase)` with `metadata = MetaData(schema=None)` (public schema)
- `TimestampMixin` provides `created_at` and `updated_at` with `func.now()` defaults
- `EntityModel.search_vector` is a `Computed` tsvector column: `to_tsvector('english', name)`
- JSONB columns use `type_=JSONB` with `server_default=text("'{}'::jsonb")`

### RLS Policies (Alembic migration)
```sql
-- Enable RLS on documents
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY documents_owner_policy ON documents
  USING (owner_id = current_setting('app.current_user_id')::uuid);

-- Enable RLS on entities (via entity_documents join)
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;
CREATE POLICY entities_owner_policy ON entities
  USING (EXISTS (
    SELECT 1 FROM entity_documents ed
    JOIN documents d ON ed.document_id = d.id
    WHERE ed.entity_id = entities.id
    AND d.owner_id = current_setting('app.current_user_id')::uuid
  ));
```

### Database Session (per-request)
```python
async def get_session(user_id: UUID | None = None):
    async with async_session_factory() as session:
        if user_id:
            await session.execute(
                text("SET LOCAL app.current_user_id = :uid"),
                {"uid": str(user_id)}
            )
        yield session
```

### Repository Pattern
- Constructor injection of `async_sessionmaker`
- Each method receives session as parameter (no internal state)
- Converts ORM models to/from domain Pydantic models
- Uses `session.get()` for PK lookups, `session.execute(select(...))` for queries

---

*Generated via SDD (Spec-Driven Development) | Engram observation #68*

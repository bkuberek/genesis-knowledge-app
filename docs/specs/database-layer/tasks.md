# Tasks: Database Layer + ACL

> **Status**: All tasks complete (implemented in SDD apply phase)

## Batch 1: Domain Layer (pure Python, no deps)

- [x] 1.1 Create `src/knowledge_core/domain/document.py` — `DocumentStatus`, `SourceType`, `Visibility` enums (StrEnum) + `Document` Pydantic model (R1)
- [x] 1.2 Create `src/knowledge_core/domain/entity.py` — `Entity` Pydantic model with JSONB properties dict (R2)
- [x] 1.3 Create `src/knowledge_core/domain/relationship.py` — `Relationship` model with confidence 0.0-1.0 validator (R3)
- [x] 1.4 Create `src/knowledge_core/domain/entity_document.py` — `EntityDocument` model, composite key (entity_id, document_id) (R4)
- [x] 1.5 Create `src/knowledge_core/domain/chat_session.py` — `ChatSession` model (R5)
- [x] 1.6 Create `src/knowledge_core/domain/chat_message.py` — `MessageRole` enum + `ChatMessage` model (R6)
- [x] 1.7 Create `src/knowledge_core/domain/user.py` — `User` model (JWT-only, no DB table) (R7)
- [x] 1.8 Update `src/knowledge_core/domain/__init__.py` — re-export all 7 entity classes and enums
- [x] 1.9 Create `src/knowledge_core/ports/database_repository_port.py` — `DatabaseRepositoryPort` ABC (R8: CRUD for documents, entities, relationships, sessions, messages)
- [x] 1.10 Create `src/knowledge_core/ports/document_storage_port.py` — `DocumentStoragePort` ABC (R9: store/retrieve/delete file bytes)
- [x] 1.11 Update `src/knowledge_core/ports/__init__.py` — re-export both port ABCs
- [x] 1.12 Create `tests/unit/test_domain_entities.py` — test creation, defaults, enum validation, confidence range rejection per spec scenarios
- [x] 1.13 Create `tests/unit/test_ports.py` — test both ports are abstract and cannot be instantiated

## Batch 2: SQLAlchemy Models + Database Infrastructure

- [x] 2.1 Create `src/knowledge_workers/adapters/models/base.py` — `Base(DeclarativeBase)`, `TimestampMixin` (created_at/updated_at)
- [x] 2.2 Create `src/knowledge_workers/adapters/models/document_model.py` — `DocumentModel` mapped to documents table (R10)
- [x] 2.3 Create `src/knowledge_workers/adapters/models/entity_model.py` — `EntityModel` with JSONB+GIN, tsvector+GIN (R11)
- [x] 2.4 Create `src/knowledge_workers/adapters/models/relationship_model.py` — `RelationshipModel` with FK cascades (R12)
- [x] 2.5 Create `src/knowledge_workers/adapters/models/entity_document_model.py` — `EntityDocumentModel` with composite PK (R13)
- [x] 2.6 Create `src/knowledge_workers/adapters/models/chat_session_model.py` — `ChatSessionModel` (R14)
- [x] 2.7 Create `src/knowledge_workers/adapters/models/chat_message_model.py` — `ChatMessageModel` with JSONB metadata (R15)
- [x] 2.8 Create `src/knowledge_workers/adapters/models/__init__.py` — re-export all models
- [x] 2.9 Create `src/knowledge_workers/adapters/database.py` — async engine factory + session factory with RLS support (R16, R17)
- [x] 2.10 Update `alembic/env.py` — import all models for autogenerate, async migration runner
- [x] 2.11 Create `alembic/versions/001_initial_schema.py` — all tables, indexes, RLS policies (R18)

## Batch 3: Repository Implementation + Integration

- [x] 3.1 Create `src/knowledge_workers/adapters/database_repository.py` — `DatabaseRepository` implementing full port (R19)
- [x] 3.2 Create `src/knowledge_workers/adapters/__init__.py` — re-export repository and database functions
- [x] 3.3 Create `tests/unit/test_database_repository.py` — unit tests with mock session for all repository methods
- [x] 3.4 **Verify**: `ruff check src/ tests/` passes, `pytest tests/unit/ -v` passes

---

*Generated via SDD (Spec-Driven Development) | Engram observation #70*

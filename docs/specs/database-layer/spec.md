# Specification: Database Layer

## Domain 1: Domain Entities

### R1: Document Entity
The system MUST define a `Document` Pydantic model with fields: id (UUID PK, default factory), filename (str), file_path (str), content_type (str), upload_date (datetime), status (enum: pending/processing/completed/failed), stage (int 1-5, default 1), source_type (enum: upload/url/api), owner_id (UUID), visibility (enum: private/public, default private), error_message (str|None), created_at (datetime), updated_at (datetime).

#### Scenario: Create valid Document
- GIVEN valid filename, content_type, owner_id
- WHEN Document is instantiated
- THEN all defaults apply (status=pending, stage=1, visibility=private, id auto-generated)

#### Scenario: Reject invalid status
- GIVEN status value not in enum
- WHEN Document is instantiated
- THEN ValidationError is raised

### R2: Entity
The system MUST define an `Entity` model: id (UUID PK), name (str), canonical_name (str), type (str), properties (dict, default {}), source_count (int, default 1), created_at, updated_at.

#### Scenario: Create Entity with properties
- GIVEN name="Apple Inc.", type="organization", properties={"sector": "tech"}
- WHEN Entity is created
- THEN properties stored as dict, source_count=1

### R3: Relationship
The system MUST define `Relationship`: id (UUID), source_entity_id (UUID), target_entity_id (UUID), relation_type (str), description (str|None), confidence (float 0.0-1.0), source_document_id (UUID), extracted_at (datetime).

#### Scenario: Reject out-of-range confidence
- GIVEN confidence=1.5
- WHEN Relationship is created
- THEN ValidationError is raised

### R4: EntityDocument
The system MUST define `EntityDocument`: entity_id (UUID), document_id (UUID), relationship (str). Composite PK on (entity_id, document_id).

### R5: ChatSession
The system MUST define `ChatSession`: id (UUID), owner_id (UUID), title (str|None), created_at, updated_at.

### R6: ChatMessage
The system MUST define `ChatMessage`: id (UUID), session_id (UUID), role (enum: user/assistant/system), content (str), metadata (dict|None), created_at.

#### Scenario: Valid message roles
- GIVEN role="user"
- WHEN ChatMessage is created
- THEN message is valid

#### Scenario: Reject invalid role
- GIVEN role="moderator"
- WHEN ChatMessage is created
- THEN ValidationError is raised

### R7: User (JWT-only)
The system MUST define a `User` model: id (UUID), email (str), username (str|None), full_name (str|None), realm_roles (list[str]). No DB table — populated from JWT claims.

---

## Domain 2: Port Interfaces

### R8: DatabaseRepositoryPort
The system MUST define an abstract `DatabaseRepositoryPort` with async methods for:
- **Documents**: create, get_by_id, list_by_owner, update_status, delete
- **Entities**: create, get_by_id, find_by_name, search_by_properties, list_by_document
- **Relationships**: create, get_by_entity, get_by_document
- **EntityDocuments**: create, get_by_entity, get_by_document
- **ChatSessions**: create, get_by_id, list_by_owner, delete
- **ChatMessages**: create, list_by_session

#### Scenario: Cannot instantiate abstract port
- GIVEN `DatabaseRepositoryPort` class
- WHEN attempting to instantiate directly
- THEN TypeError is raised

### R9: DocumentStoragePort
The system MUST define an abstract `DocumentStoragePort` with async methods: store(filename, content) -> path, retrieve(path) -> bytes, delete(path), exists(path) -> bool.

---

## Domain 3: SQLAlchemy Models

### R10: Document Model
`DocumentModel` MUST map to `documents` table with all R1 fields as columns. Status, source_type, and visibility MUST use PostgreSQL enum types. Timestamps MUST default to `func.now()`.

### R11: Entity Model
`EntityModel` MUST map to `entities` table with JSONB `properties` column, `search_vector` tsvector column, GIN index on properties, GIN index on search_vector, unique constraint on `(canonical_name, type)`.

### R12: Relationship Model
`RelationshipModel` MUST map to `relationships` table with foreign keys to entities (source, target) and documents (source_document). Cascade delete on entity deletion.

### R13: EntityDocument Model
`EntityDocumentModel` MUST map to `entity_documents` table with composite PK, foreign keys to entities and documents with cascade delete.

### R14: ChatSession Model
`ChatSessionModel` MUST map to `chat_sessions` table with owner_id indexed.

### R15: ChatMessage Model
`ChatMessageModel` MUST map to `chat_messages` table with foreign key to chat_sessions (cascade delete), JSONB metadata column.

---

## Domain 4: Database Infrastructure

### R16: Async Engine Factory
`create_async_engine_from_config()` MUST create an AsyncEngine from dynaconf settings, using `postgresql+asyncpg` URL.

### R17: Session Factory
`get_async_session()` MUST return an async context manager yielding sessions with `expire_on_commit=False`. Each session MUST execute `SET LOCAL app.current_user_id` when a user_id is provided (for RLS).

### R18: Alembic Migration
Initial migration MUST create all 6 tables, all indexes, and RLS policies. RLS policies:
- `documents`: filter by `owner_id = current_setting('app.current_user_id')::uuid`
- `entities`: filter via join to `entity_documents -> documents` by owner_id
- `chat_sessions` + `chat_messages`: filter by session owner_id

---

## Domain 5: Repository Implementation

### R19: DatabaseRepository
`DatabaseRepository` MUST implement `DatabaseRepositoryPort` using async SQLAlchemy sessions. All methods MUST:
- Accept an async session parameter
- Use parameterized queries (no string interpolation)
- Convert between domain models and ORM models
- Handle `IntegrityError` for unique constraint violations

#### Scenario: Create and retrieve document
- GIVEN a valid Document domain object
- WHEN calling `create_document(session, document)`
- THEN document is persisted and `get_document_by_id(session, id)` returns it

#### Scenario: RLS filters by owner
- GIVEN documents owned by user A and user B
- WHEN user A queries `list_documents_by_owner(session)`
- THEN only user A's documents are returned

---

*Generated via SDD (Spec-Driven Development) | Engram observation #67*

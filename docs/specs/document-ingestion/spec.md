# Document Ingestion Pipeline — Specification

**Phase**: 3
**Status**: Implemented (retroactive spec)
**Change**: document-ingestion-pipeline

## Intent

Build the complete document ingestion pipeline — from raw file upload through text parsing,
LLM-powered entity extraction, entity resolution/deduplication, and persistence to PostgreSQL.
This is the core data flow of the knowledge app: documents go in, structured entities and
relationships come out.

## Key Requirements

### REQ-3.1: LLM Port Interface

**GIVEN** the hexagonal architecture with ports in `knowledge_core`
**WHEN** the system needs to call an LLM for entity extraction or chat
**THEN** an abstract `LLMPort` must define two async methods: `complete()` for simple
text completions and `complete_with_tools()` for tool-calling interactions, both accepting
messages, model, temperature, and max_tokens parameters.

### REQ-3.2: LiteLLM Client Adapter

**GIVEN** the `LLMPort` interface exists
**WHEN** the application needs to call an LLM provider
**THEN** `LLMClient` must implement `LLMPort` using `litellm.acompletion()`, reading
API base URL, API key, and default model from dynaconf settings with env var fallback
via `_resolve_setting()`.

### REQ-3.3: Document Parsers

**GIVEN** documents of various formats (CSV, PDF, DOCX, plain text, URL)
**WHEN** a document needs to be ingested
**THEN** the system must provide a parser for each supported format, all inheriting from
`BaseParser` with `parse(file_path) -> str` and `supports(content_type) -> bool` methods.
A `get_parser(content_type)` registry function must select the correct parser.

### REQ-3.4: Entity Extractor

**GIVEN** parsed text content from a document
**WHEN** entity extraction is triggered
**THEN** `EntityExtractor` must send a structured prompt to the LLM requesting entities
(name, type, properties) and relationships (source, target, relation_type, description,
confidence) in JSON format, parsing the LLM response and stripping markdown code blocks.

### REQ-3.5: Entity Resolver

**GIVEN** newly extracted entities and existing entities in the database
**WHEN** entities are resolved against the knowledge base
**THEN** `EntityResolver` must use 3-layer matching: (1) exact canonical name match,
(2) fuzzy match via `SequenceMatcher` with threshold ≥ 0.85, and (3) create new entity
if no match. Corporate suffixes (Inc, LLC, Ltd, Corp) must be stripped during
canonicalization. Matched entities must merge properties and increment `source_count`.

### REQ-3.6: Ingestion Pipeline Orchestrator

**GIVEN** a file upload or URL submission
**WHEN** document ingestion is initiated
**THEN** `IngestionPipeline` must execute 5 stages in order: (1) store file to disk,
(2) parse content to text, (3) extract entities via LLM, (4) resolve against existing
entities, (5) save entities and relationships to database. Each stage must update the
document's status and stage number. Errors must be caught and recorded on the document.

### REQ-3.7: Hexagonal Purity for IngestionService

**GIVEN** the domain layer must have zero framework dependencies
**WHEN** processing already-parsed text through the extraction pipeline
**THEN** `IngestionService` in `knowledge_core/services/` must accept pre-parsed text
(not raw files), delegating file I/O to the `IngestionPipeline` in `knowledge_workers`.

### REQ-3.8: Document Storage Adapter

**GIVEN** uploaded files need to be persisted to disk
**WHEN** a file is ingested
**THEN** `FileDocumentStorage` must implement `DocumentStoragePort`, saving files to the
configured `storage.document_path` directory organized by document ID.

### REQ-3.9: Tool Call Argument Parsing

**GIVEN** LLM providers return tool call arguments in inconsistent formats
**WHEN** `LLMClient` parses a tool call response
**THEN** it must handle arguments as either `str` (needing `json.loads`) or `dict`
(already parsed), using an `isinstance` check.

## Implementation Summary

### Files Created/Modified

- `src/knowledge_core/ports/llm_port.py` — Abstract LLM interface (complete, complete_with_tools)
- `src/knowledge_core/ports/__init__.py` — Updated exports
- `src/knowledge_core/services/ingestion_service.py` — Domain-pure extraction orchestrator
- `src/knowledge_workers/llm/llm_client.py` — LiteLLM wrapper with env var fallback
- `src/knowledge_workers/parsers/base_parser.py` — Abstract parser base class
- `src/knowledge_workers/parsers/csv_parser.py` — CSV file parser
- `src/knowledge_workers/parsers/pdf_parser.py` — PDF file parser
- `src/knowledge_workers/parsers/docx_parser.py` — DOCX file parser
- `src/knowledge_workers/parsers/text_parser.py` — Plain text parser
- `src/knowledge_workers/parsers/url_parser.py` — URL content parser
- `src/knowledge_workers/parsers/__init__.py` — Parser registry with `get_parser()`
- `src/knowledge_workers/ingestion/entity_extractor.py` — LLM-based entity extraction
- `src/knowledge_workers/ingestion/entity_resolver.py` — 3-layer entity matching
- `src/knowledge_workers/ingestion/pipeline.py` — Full pipeline orchestrator
- `src/knowledge_workers/adapters/document_storage.py` — File storage adapter
- `tests/unit/test_parsers.py` — Parser unit tests
- `tests/unit/test_entity_resolver.py` — Resolver unit tests
- `tests/unit/test_entity_extractor.py` — Extractor unit tests
- `tests/unit/test_llm_client.py` — LLM client unit tests

### Key Patterns & Decisions

- `IngestionService` (domain) accepts pre-parsed text; `IngestionPipeline` (workers) handles
  the full file → parse → extract → save flow — maintaining hexagonal purity
- `EntityResolver` uses a `working_entities` list that grows during resolution so subsequent
  entities in the same batch can match against newly created ones
- `get_parser()` registry uses content-type matching, not file extensions
- LLM prompts request JSON-only responses; code block markers are stripped as a fallback

## Discoveries

- `ruff UP015` catches unnecessary `mode="r"` arguments on file opens
- LiteLLM `tool_call.function.arguments` can be `str` or `dict` depending on the LLM
  provider — always handle both with `isinstance` check
- Corporate suffix stripping in `canonicalize()` must handle both "inc" and "inc." variants
- The extraction prompt must explicitly say "Return ONLY valid JSON, no markdown formatting"
  to avoid LLM wrapping responses in code blocks

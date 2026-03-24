import uuid
from typing import Any

from knowledge_core.domain.document import Document, DocumentStatus, SourceType
from knowledge_core.domain.entity import Entity
from knowledge_core.domain.relationship import Relationship
from knowledge_core.ports.database_repository_port import DatabaseRepositoryPort
from knowledge_core.ports.document_storage_port import DocumentStoragePort
from knowledge_core.ports.llm_port import LLMPort
from knowledge_workers.ingestion.entity_extractor import EntityExtractor
from knowledge_workers.ingestion.entity_resolver import EntityResolver
from knowledge_workers.parsers import get_parser
from knowledge_workers.parsers.csv_parser import SUPPORTED_CONTENT_TYPES as CSV_CONTENT_TYPES
from knowledge_workers.parsers.csv_parser import CsvParser

MAX_EXISTING_ENTITIES_LIMIT = 1000


class IngestionPipeline:
    """Full document ingestion pipeline: store, parse, extract, resolve, save.

    Orchestrates the complete flow from raw file/URL to extracted entities
    and relationships stored in the database. CSV files are parsed directly
    into entities without LLM extraction.
    """

    def __init__(
        self,
        repository: DatabaseRepositoryPort,
        storage: DocumentStoragePort,
        llm_client: LLMPort,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._extractor = EntityExtractor(llm_client)
        self._resolver = EntityResolver()

    async def ingest_file(
        self,
        owner_id: uuid.UUID,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> Document:
        """Ingest a file through the full pipeline."""
        document = Document(
            filename=filename,
            content_type=content_type,
            source_type=SourceType.FILE,
            owner_id=owner_id,
        )
        document = await self._repository.save_document(document)

        try:
            file_path = await self._store_file(document, filename, content)
            if self._is_csv(content_type):
                return await self._extract_csv_entities(document, file_path)
            text = await self._parse_content(document, content_type, file_path)
            return await self._extract_and_save(document, text, filename)
        except Exception as exc:
            return await self._handle_pipeline_error(document, exc)

    async def process_existing_document(
        self,
        document: Document,
        content: bytes,
    ) -> Document:
        """Process an already-saved document through the pipeline.

        Used for background processing after the document record has been
        created and returned to the client.
        """
        try:
            file_path = await self._store_file(
                document,
                document.filename,
                content,
            )
            content_type = document.content_type or ""
            if self._is_csv(content_type):
                return await self._extract_csv_entities(document, file_path)
            text = await self._parse_content(document, content_type, file_path)
            return await self._extract_and_save(document, text, document.filename)
        except Exception as exc:
            return await self._handle_pipeline_error(document, exc)

    async def ingest_url(
        self,
        owner_id: uuid.UUID,
        url: str,
    ) -> Document:
        """Ingest content from a URL through the full pipeline."""
        document = Document(
            filename=url,
            content_type="url",
            source_type=SourceType.URL,
            owner_id=owner_id,
        )
        document = await self._repository.save_document(document)

        try:
            text = await self._parse_content(document, "url", url)
            return await self._extract_and_save(document, text, url)
        except Exception as exc:
            return await self._handle_pipeline_error(document, exc)

    # -- CSV direct extraction (no LLM) -----------------------------------

    async def _extract_csv_entities(
        self,
        document: Document,
        file_path: str,
    ) -> Document:
        """Extract entities directly from CSV rows without LLM.

        Structured data doesn't need LLM interpretation — each row
        becomes an entity with columns as typed properties.
        """
        await self._update_status(document.id, DocumentStatus.PROCESSING, stage=2)
        csv_parser = CsvParser()
        raw_entities = csv_parser.extract_entities(file_path)

        await self._update_status(document.id, DocumentStatus.PROCESSING, stage=4)
        existing_entities = await self._repository.search_entities(
            "",
            limit=MAX_EXISTING_ENTITIES_LIMIT,
        )
        resolved_entities = self._resolver.resolve(raw_entities, existing_entities)

        await self._update_status(document.id, DocumentStatus.PROCESSING, stage=5)
        await self._repository.save_entities(resolved_entities, document.id)

        await self._update_status(document.id, DocumentStatus.COMPLETE, stage=5)
        return document.model_copy(
            update={
                "status": DocumentStatus.COMPLETE,
                "stage": 5,
            }
        )

    # -- LLM extraction (for unstructured formats) ------------------------

    async def _store_file(
        self,
        document: Document,
        filename: str,
        content: bytes,
    ) -> str:
        """Stage 1: Store file to disk."""
        await self._update_status(document.id, DocumentStatus.PROCESSING, stage=1)
        return await self._storage.save_file(document.id, filename, content)

    async def _parse_content(
        self,
        document: Document,
        content_type: str,
        source_path: str,
    ) -> str:
        """Stage 2: Parse content into text."""
        await self._update_status(document.id, DocumentStatus.PROCESSING, stage=2)
        parser = get_parser(content_type)
        return await parser.parse(source_path)

    async def _extract_and_save(
        self,
        document: Document,
        text: str,
        source_name: str,
    ) -> Document:
        """Stages 3-5: Extract entities, resolve, and save to database."""
        await self._update_status(document.id, DocumentStatus.PROCESSING, stage=3)
        extraction = await self._extractor.extract(
            text,
            f"Document: {source_name}",
        )

        await self._update_status(document.id, DocumentStatus.PROCESSING, stage=4)
        existing_entities = await self._repository.search_entities(
            "",
            limit=MAX_EXISTING_ENTITIES_LIMIT,
        )
        resolved_entities = self._resolver.resolve(
            extraction.get("entities", []),
            existing_entities,
        )

        await self._update_status(document.id, DocumentStatus.PROCESSING, stage=5)
        saved_entities = await self._repository.save_entities(
            resolved_entities,
            document.id,
        )

        relationships = self._build_relationships(
            extraction.get("relationships", []),
            saved_entities,
            document.id,
        )
        if relationships:
            await self._repository.save_relationships(relationships)

        await self._update_status(document.id, DocumentStatus.COMPLETE, stage=5)
        return document.model_copy(
            update={
                "status": DocumentStatus.COMPLETE,
                "stage": 5,
            }
        )

    # -- Shared helpers ---------------------------------------------------

    @staticmethod
    def _is_csv(content_type: str) -> bool:
        """Check if the content type represents a CSV file."""
        return content_type in CSV_CONTENT_TYPES

    async def _handle_pipeline_error(
        self,
        document: Document,
        error: Exception,
    ) -> Document:
        """Handle pipeline errors by updating document status."""
        await self._update_status(
            document.id,
            DocumentStatus.ERROR,
            error_message=str(error),
        )
        return document.model_copy(
            update={
                "status": DocumentStatus.ERROR,
                "error_message": str(error),
            }
        )

    async def _update_status(
        self,
        document_id: uuid.UUID,
        status: DocumentStatus,
        stage: int | None = None,
        error_message: str | None = None,
    ) -> None:
        """Update document processing status in the repository."""
        await self._repository.update_document_status(
            document_id,
            status,
            stage=stage,
            error_message=error_message,
        )

    def _build_relationships(
        self,
        raw_relationships: list[dict[str, Any]],
        saved_entities: list[Entity],
        document_id: uuid.UUID,
    ) -> list[Relationship]:
        """Build Relationship domain objects from extracted relationship data."""
        entity_lookup = {entity.name.lower(): entity for entity in saved_entities}
        relationships: list[Relationship] = []
        for rel_data in raw_relationships:
            source = entity_lookup.get(rel_data.get("source", "").lower())
            target = entity_lookup.get(rel_data.get("target", "").lower())
            if source is None or target is None:
                continue
            relationships.append(
                Relationship(
                    source_entity_id=source.id,
                    target_entity_id=target.id,
                    relation_type=rel_data.get("relation_type", "related_to"),
                    description=rel_data.get("description"),
                    confidence=rel_data.get("confidence", 0.9),
                    source_document_id=document_id,
                )
            )
        return relationships

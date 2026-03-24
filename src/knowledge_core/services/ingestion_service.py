import uuid
from typing import Any

from knowledge_core.domain.document import Document, DocumentStatus
from knowledge_core.domain.entity import Entity
from knowledge_core.domain.relationship import Relationship
from knowledge_core.ports.database_repository_port import DatabaseRepositoryPort
from knowledge_core.ports.llm_port import LLMPort

MAX_EXISTING_ENTITIES_LIMIT = 1000


class IngestionService:
    """Application service for the entity extraction pipeline.

    Orchestrates document processing: LLM-based entity extraction,
    entity resolution against existing records, and persistence.
    Accepts pre-parsed text to maintain hexagonal architecture purity.

    For CSV documents, use ``process_csv_entities`` to bypass LLM extraction.
    """

    def __init__(
        self,
        repository: DatabaseRepositoryPort,
        llm_client: LLMPort,
    ) -> None:
        self._repository = repository
        self._llm = llm_client

    async def process_document(
        self,
        document: Document,
        text_content: str,
    ) -> Document:
        """Process a document's text content through the extraction pipeline.

        Expects the document to already be saved to the database and
        the text to already be parsed from the source file/URL.
        """
        from knowledge_workers.ingestion.entity_extractor import (
            EntityExtractor,
        )
        from knowledge_workers.ingestion.entity_resolver import (
            EntityResolver,
        )

        extractor = EntityExtractor(self._llm)
        resolver = EntityResolver()

        try:
            await self._update_status(document.id, DocumentStatus.PROCESSING, stage=3)
            extraction = await extractor.extract(
                text_content,
                document_context=f"Document: {document.filename}",
            )

            await self._update_status(document.id, DocumentStatus.PROCESSING, stage=4)
            existing_entities = await self._repository.search_entities(
                "",
                limit=MAX_EXISTING_ENTITIES_LIMIT,
            )
            resolved_entities = resolver.resolve(
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

        except Exception as exc:
            await self._update_status(
                document.id,
                DocumentStatus.ERROR,
                error_message=str(exc),
            )
            return document.model_copy(
                update={
                    "status": DocumentStatus.ERROR,
                    "error_message": str(exc),
                }
            )

    async def process_csv_entities(
        self,
        document: Document,
        raw_entities: list[dict[str, Any]],
    ) -> Document:
        """Process pre-extracted CSV entities through resolution and persistence.

        Accepts entity dicts from CsvParser.extract_entities(), resolves
        against existing entities, and saves without LLM involvement.
        """
        from knowledge_workers.ingestion.entity_resolver import EntityResolver

        resolver = EntityResolver()

        try:
            await self._update_status(document.id, DocumentStatus.PROCESSING, stage=4)
            existing_entities = await self._repository.search_entities(
                "",
                limit=MAX_EXISTING_ENTITIES_LIMIT,
            )
            resolved_entities = resolver.resolve(raw_entities, existing_entities)

            await self._update_status(document.id, DocumentStatus.PROCESSING, stage=5)
            await self._repository.save_entities(resolved_entities, document.id)

            await self._update_status(document.id, DocumentStatus.COMPLETE, stage=5)
            return document.model_copy(
                update={
                    "status": DocumentStatus.COMPLETE,
                    "stage": 5,
                }
            )

        except Exception as exc:
            await self._update_status(
                document.id,
                DocumentStatus.ERROR,
                error_message=str(exc),
            )
            return document.model_copy(
                update={
                    "status": DocumentStatus.ERROR,
                    "error_message": str(exc),
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

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from knowledge_api.dependencies.auth import get_current_user
from knowledge_api.dependencies.container import container
from knowledge_api.schemas.entity_schemas import (
    EntityResponse,
    EntitySearchResponse,
    KnowledgeAddRequest,
    RelationshipResponse,
)
from knowledge_core.domain.document import Document, SourceType  # noqa: TCH001
from knowledge_core.domain.user import User  # noqa: TCH001

router = APIRouter(prefix="/graph", tags=["graph"])

MAX_EXISTING_ENTITIES_FOR_RESOLUTION = 1000


@router.get(
    "/search",
    operation_id="search_knowledge",
    response_model=EntitySearchResponse,
)
async def search_knowledge(
    q: str = Query(default="", description="Search query"),
    entity_type: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    user: User = Depends(get_current_user),  # noqa: B008
) -> EntitySearchResponse:
    """Search entities in the knowledge graph."""
    entities = await container.repository.search_entities(
        q,
        entity_type,
        limit,
    )
    return EntitySearchResponse(
        entities=[
            EntityResponse(
                id=e.id,
                name=e.name,
                canonical_name=e.canonical_name,
                type=e.type,
                properties=e.properties,
                source_count=e.source_count,
            )
            for e in entities
        ],
        total=len(entities),
    )


@router.get(
    "/entities/{entity_id}",
    operation_id="get_entity",
    response_model=EntityResponse,
)
async def get_entity(
    entity_id: uuid.UUID,
    user: User = Depends(get_current_user),  # noqa: B008
) -> EntityResponse:
    """Get a specific entity by ID."""
    entity = await container.repository.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return EntityResponse(
        id=entity.id,
        name=entity.name,
        canonical_name=entity.canonical_name,
        type=entity.type,
        properties=entity.properties,
        source_count=entity.source_count,
    )


@router.get(
    "/entities/{entity_id}/relationships",
    operation_id="get_entity_relationships",
)
async def get_entity_relationships(
    entity_id: uuid.UUID,
    user: User = Depends(get_current_user),  # noqa: B008
) -> dict:
    """Get all relationships for an entity."""
    rels = await container.repository.get_entity_relationships(entity_id)
    return {
        "relationships": [
            RelationshipResponse(
                id=r.id,
                source_entity_id=r.source_entity_id,
                target_entity_id=r.target_entity_id,
                relation_type=r.relation_type,
                description=r.description,
                confidence=r.confidence,
            )
            for r in rels
        ],
    }


@router.post(
    "/knowledge",
    operation_id="add_knowledge",
    status_code=201,
)
async def add_knowledge(
    request: KnowledgeAddRequest,
    user: User = Depends(get_current_user),  # noqa: B008
) -> dict:
    """Add knowledge from text directly."""
    document = Document(
        filename=f"manual-{request.source}",
        content_type="text/plain",
        source_type=SourceType.FILE,
        owner_id=user.id,
    )
    document = await container.repository.save_document(document)

    from knowledge_workers.ingestion.entity_extractor import EntityExtractor
    from knowledge_workers.ingestion.entity_resolver import EntityResolver

    extractor = EntityExtractor(container.llm_client)
    resolver = EntityResolver()
    extraction = await extractor.extract(request.text, request.source)
    existing = await container.repository.search_entities(
        "",
        limit=MAX_EXISTING_ENTITIES_FOR_RESOLUTION,
    )
    resolved = resolver.resolve(extraction.get("entities", []), existing)
    await container.repository.save_entities(resolved, document.id)
    return {
        "document_id": str(document.id),
        "entities_extracted": len(resolved),
    }

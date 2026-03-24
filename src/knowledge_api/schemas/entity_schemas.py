import uuid
from typing import Any

from pydantic import BaseModel


class EntityResponse(BaseModel):
    id: uuid.UUID
    name: str
    canonical_name: str
    type: str
    properties: dict[str, Any]
    source_count: int


class EntitySearchResponse(BaseModel):
    entities: list[EntityResponse]
    total: int


class RelationshipResponse(BaseModel):
    id: uuid.UUID
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relation_type: str
    description: str | None
    confidence: float


class KnowledgeAddRequest(BaseModel):
    """Request body for adding knowledge via text."""

    text: str
    source: str = "manual"

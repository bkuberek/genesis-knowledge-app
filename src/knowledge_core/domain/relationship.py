import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class Relationship(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relation_type: str
    description: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_document_id: uuid.UUID | None = None
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

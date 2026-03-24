import uuid

from pydantic import BaseModel


class EntityDocument(BaseModel):
    entity_id: uuid.UUID
    document_id: uuid.UUID
    relationship: str = "extracted_from"

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class Entity(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    canonical_name: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)
    source_count: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

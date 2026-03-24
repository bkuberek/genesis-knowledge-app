import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ChatSession(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    owner_id: uuid.UUID
    title: str = "New Chat"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

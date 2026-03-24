import enum
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class DocumentStatus(enum.StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETE = "complete"
    ERROR = "error"


class SourceType(enum.StrEnum):
    FILE = "file"
    URL = "url"


class Visibility(enum.StrEnum):
    PRIVATE = "private"
    PUBLIC = "public"


class Document(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    filename: str
    file_path: str | None = None
    content_type: str | None = None
    upload_date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: DocumentStatus = DocumentStatus.QUEUED
    stage: int = Field(default=0, ge=0, le=5)
    source_type: SourceType = SourceType.FILE
    owner_id: uuid.UUID
    visibility: Visibility = Visibility.PRIVATE
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

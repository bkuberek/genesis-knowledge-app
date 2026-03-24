import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    filename: str
    status: str
    created_at: datetime


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    file_path: str | None
    content_type: str | None
    status: str
    stage: int
    source_type: str
    visibility: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]


class UrlUploadRequest(BaseModel):
    url: str

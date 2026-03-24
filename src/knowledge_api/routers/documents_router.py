import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from knowledge_api.dependencies.auth import get_current_user
from knowledge_api.dependencies.container import container
from knowledge_api.schemas.document_schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
    UrlUploadRequest,
)
from knowledge_core.domain.document import Document, SourceType  # noqa: TCH001
from knowledge_core.domain.user import User  # noqa: TCH001

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

CONTENT_TYPE_BY_EXTENSION = {
    "csv": "text/csv",
    "pdf": "application/pdf",
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "txt": "text/plain",
}


def _guess_content_type(filename: str) -> str:
    """Guess MIME type from filename extension."""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return CONTENT_TYPE_BY_EXTENSION.get(extension, "application/octet-stream")


def _document_to_response(doc: Document) -> DocumentResponse:
    """Convert a domain Document to an API response."""
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        file_path=doc.file_path,
        content_type=doc.content_type,
        status=doc.status.value,
        stage=doc.stage,
        source_type=doc.source_type.value,
        visibility=doc.visibility.value,
        error_message=doc.error_message,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=201,
    operation_id="upload_document",
)
async def upload_document(
    file: UploadFile = File(...),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> DocumentUploadResponse:
    """Upload a document for processing."""
    content = await file.read()
    content_type = file.content_type or _guess_content_type(
        file.filename or "",
    )

    document = Document(
        filename=file.filename or "unnamed",
        content_type=content_type,
        source_type=SourceType.FILE,
        owner_id=user.id,
    )
    document = await container.repository.save_document(document)

    asyncio.create_task(
        container.ingestion_pipeline.process_existing_document(
            document=document,
            content=content,
        )
    )

    return DocumentUploadResponse(
        id=document.id,
        filename=document.filename,
        status=document.status.value,
        created_at=document.created_at,
    )


@router.post(
    "/url",
    response_model=DocumentUploadResponse,
    status_code=201,
    operation_id="upload_url",
)
async def upload_url(
    request: UrlUploadRequest,
    user: User = Depends(get_current_user),  # noqa: B008
) -> DocumentUploadResponse:
    """Ingest content from a URL."""
    document = await container.ingestion_pipeline.ingest_url(
        owner_id=user.id,
        url=request.url,
    )
    return DocumentUploadResponse(
        id=document.id,
        filename=document.filename,
        status=document.status.value,
        created_at=document.created_at,
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    operation_id="list_documents",
)
async def list_documents(
    user: User = Depends(get_current_user),  # noqa: B008
) -> DocumentListResponse:
    """List the current user's documents."""
    docs = await container.repository.list_documents(user.id)
    return DocumentListResponse(
        documents=[_document_to_response(d) for d in docs],
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    operation_id="get_document",
)
async def get_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),  # noqa: B008
) -> DocumentResponse:
    """Get a single document by ID."""
    doc = await container.repository.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _document_to_response(doc)


@router.get(
    "/{document_id}/entities",
    operation_id="get_document_entities",
)
async def get_document_entities(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),  # noqa: B008
) -> dict:
    """Get entities extracted from a specific document."""
    entities = await container.repository.search_entities("", limit=100)
    return {"entities": [e.model_dump() for e in entities]}

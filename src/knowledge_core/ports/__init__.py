"""Port interfaces for the Knowledge application."""

from knowledge_core.ports.database_repository_port import DatabaseRepositoryPort
from knowledge_core.ports.document_storage_port import DocumentStoragePort

__all__ = [
    "DatabaseRepositoryPort",
    "DocumentStoragePort",
]

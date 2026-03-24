import os
import uuid

import aiofiles

from knowledge_core.config import settings
from knowledge_core.ports.document_storage_port import DocumentStoragePort


class FileDocumentStorage(DocumentStoragePort):
    """File system storage implementing the document storage port."""

    def __init__(self) -> None:
        self._base_path = settings.storage.document_path

    async def save_file(
        self,
        document_id: uuid.UUID,
        filename: str,
        content: bytes,
    ) -> str:
        """Save a file to disk and return its path."""
        directory_path = os.path.join(self._base_path, str(document_id))
        os.makedirs(directory_path, exist_ok=True)
        file_path = os.path.join(directory_path, filename)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        return file_path

    async def get_file(self, file_path: str) -> bytes:
        """Read and return file contents from disk."""
        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()

    async def delete_file(self, file_path: str) -> None:
        """Delete a file from disk if it exists."""
        if os.path.exists(file_path):
            os.remove(file_path)

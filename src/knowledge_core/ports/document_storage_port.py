import abc
import uuid


class DocumentStoragePort(abc.ABC):
    """Abstract interface for document file storage."""

    @abc.abstractmethod
    async def save_file(
        self,
        document_id: uuid.UUID,
        filename: str,
        content: bytes,
    ) -> str: ...

    @abc.abstractmethod
    async def get_file(self, file_path: str) -> bytes: ...

    @abc.abstractmethod
    async def delete_file(self, file_path: str) -> None: ...

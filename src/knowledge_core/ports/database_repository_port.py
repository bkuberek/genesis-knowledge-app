import abc
import uuid
from typing import Any

from knowledge_core.domain.chat_message import ChatMessage
from knowledge_core.domain.chat_session import ChatSession
from knowledge_core.domain.document import Document, DocumentStatus
from knowledge_core.domain.entity import Entity
from knowledge_core.domain.relationship import Relationship


class DatabaseRepositoryPort(abc.ABC):
    """Abstract interface for database operations."""

    # Document operations

    @abc.abstractmethod
    async def save_document(self, document: Document) -> Document: ...

    @abc.abstractmethod
    async def get_document(self, document_id: uuid.UUID) -> Document | None: ...

    @abc.abstractmethod
    async def list_documents(self, owner_id: uuid.UUID) -> list[Document]: ...

    @abc.abstractmethod
    async def update_document_status(
        self,
        document_id: uuid.UUID,
        status: DocumentStatus,
        stage: int | None = None,
        error_message: str | None = None,
    ) -> None: ...

    # Entity operations

    @abc.abstractmethod
    async def save_entities(
        self,
        entities: list[Entity],
        document_id: uuid.UUID,
    ) -> list[Entity]: ...

    @abc.abstractmethod
    async def get_entity(self, entity_id: uuid.UUID) -> Entity | None: ...

    @abc.abstractmethod
    async def search_entities(
        self,
        query: str,
        entity_type: str | None = None,
        limit: int = 20,
    ) -> list[Entity]: ...

    @abc.abstractmethod
    async def get_entity_relationships(
        self,
        entity_id: uuid.UUID,
    ) -> list[Relationship]: ...

    # Relationship operations

    @abc.abstractmethod
    async def save_relationships(
        self,
        relationships: list[Relationship],
    ) -> list[Relationship]: ...

    # Chat operations

    @abc.abstractmethod
    async def create_chat_session(
        self,
        owner_id: uuid.UUID,
        title: str = "New Chat",
    ) -> ChatSession: ...

    @abc.abstractmethod
    async def get_chat_sessions(
        self,
        owner_id: uuid.UUID,
    ) -> list[ChatSession]: ...

    @abc.abstractmethod
    async def get_chat_session(
        self,
        session_id: uuid.UUID,
    ) -> ChatSession | None: ...

    @abc.abstractmethod
    async def update_chat_session(
        self,
        session_id: uuid.UUID,
        title: str,
    ) -> None: ...

    @abc.abstractmethod
    async def delete_chat_session(
        self,
        session_id: uuid.UUID,
    ) -> None: ...

    @abc.abstractmethod
    async def save_chat_message(
        self,
        message: ChatMessage,
    ) -> ChatMessage: ...

    @abc.abstractmethod
    async def get_chat_messages(
        self,
        session_id: uuid.UUID,
    ) -> list[ChatMessage]: ...

    # Query operations (for chat agent tools)

    @abc.abstractmethod
    async def describe_entity_schema(self) -> dict[str, Any]: ...

    @abc.abstractmethod
    async def query_entities(
        self,
        entity_type: str | None = None,
        filters: list[dict[str, Any]] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
        limit: int = 20,
    ) -> list[Entity]: ...

    @abc.abstractmethod
    async def aggregate_entities(
        self,
        entity_type: str | None = None,
        property_name: str | None = None,
        operation: str = "count",
        group_by: str | None = None,
    ) -> list[dict[str, Any]]: ...

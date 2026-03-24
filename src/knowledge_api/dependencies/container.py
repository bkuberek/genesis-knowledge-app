"""Dependency injection container — wires all adapters and services."""

from sqlalchemy.ext.asyncio import (  # noqa: TCH002
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from knowledge_core.ports.auth_port import AuthPort  # noqa: TCH001
from knowledge_core.ports.database_repository_port import (  # noqa: TCH001
    DatabaseRepositoryPort,
)
from knowledge_core.ports.llm_port import LLMPort  # noqa: TCH001
from knowledge_workers.adapters.database import (
    create_engine,
    create_session_factory,
)
from knowledge_workers.adapters.database_repository import DatabaseRepository
from knowledge_workers.adapters.document_storage import FileDocumentStorage
from knowledge_workers.adapters.keycloak_auth import KeycloakAuthAdapter
from knowledge_workers.ingestion.pipeline import IngestionPipeline
from knowledge_workers.llm.llm_client import LLMClient


class Container:
    """Dependency injection container — wires all adapters and services."""

    def __init__(self) -> None:
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None
        self.repository: DatabaseRepositoryPort | None = None
        self.auth_adapter: AuthPort | None = None
        self.llm_client: LLMPort | None = None
        self.ingestion_pipeline: IngestionPipeline | None = None

    async def initialize(self) -> None:
        """Wire all dependencies at application startup."""
        self.engine = create_engine()
        self.session_factory = create_session_factory(self.engine)
        self.repository = DatabaseRepository(self.session_factory)
        self.auth_adapter = KeycloakAuthAdapter()
        self.llm_client = LLMClient()
        storage = FileDocumentStorage()
        self.ingestion_pipeline = IngestionPipeline(
            repository=self.repository,
            storage=storage,
            llm_client=self.llm_client,
        )

    async def shutdown(self) -> None:
        """Clean up resources at application shutdown."""
        if self.engine:
            await self.engine.dispose()


container = Container()

"""SQLAlchemy model for the entity_documents join table."""

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_workers.adapters.models.base import Base


class EntityDocumentModel(Base):
    """Maps to the entity_documents table (composite PK)."""

    __tablename__ = "entity_documents"

    entity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("entities.id"),
        primary_key=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id"),
        primary_key=True,
    )
    relationship: Mapped[str] = mapped_column(
        String,
        default="extracted_from",
    )

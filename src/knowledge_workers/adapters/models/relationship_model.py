"""SQLAlchemy model for the relationships table."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_workers.adapters.models.base import Base


class RelationshipModel(Base):
    """Maps to the relationships table."""

    __tablename__ = "relationships"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("entities.id"),
        nullable=False,
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("entities.id"),
        nullable=False,
    )
    relation_type: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(default=1.0)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id"),
        nullable=True,
    )
    extracted_at: Mapped[datetime] = mapped_column(server_default=func.now())

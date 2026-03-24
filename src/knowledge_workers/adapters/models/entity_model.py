"""SQLAlchemy model for the entities table."""

import uuid

from sqlalchemy import Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_workers.adapters.models.base import Base, TimestampMixin


class EntityModel(TimestampMixin, Base):
    """Maps to the entities table."""

    __tablename__ = "entities"
    __table_args__ = (
        Index(
            "ix_entities_properties",
            "properties",
            postgresql_using="gin",
        ),
        Index(
            "ix_entities_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
        Index(
            "ix_entities_canonical_name_type",
            "canonical_name",
            "type",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    canonical_name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    properties: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    source_count: Mapped[int] = mapped_column(default=1)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        nullable=True,
    )

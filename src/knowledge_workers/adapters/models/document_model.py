"""SQLAlchemy model for the documents table."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_workers.adapters.models.base import Base, TimestampMixin


class DocumentModel(TimestampMixin, Base):
    """Maps to the documents table."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String, nullable=True)
    upload_date: Mapped[datetime] = mapped_column(server_default=func.now())
    status: Mapped[str] = mapped_column(String, default="queued")
    stage: Mapped[int] = mapped_column(default=0)
    source_type: Mapped[str] = mapped_column(String, default="file")
    owner_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    visibility: Mapped[str] = mapped_column(String, default="private")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

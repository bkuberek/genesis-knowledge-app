"""SQLAlchemy model for the chat_sessions table."""

import uuid

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_workers.adapters.models.base import Base, TimestampMixin


class ChatSessionModel(TimestampMixin, Base):
    """Maps to the chat_sessions table."""

    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, default="New Chat")

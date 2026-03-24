import uuid

from pydantic import BaseModel


class User(BaseModel):
    """User value object — resolved from JWT, not stored in database."""

    id: uuid.UUID
    email: str
    name: str = ""

import abc

from knowledge_core.domain.user import User


class AuthPort(abc.ABC):
    """Abstract interface for authentication operations."""

    @abc.abstractmethod
    async def validate_token(self, token: str) -> User:
        """Validate a JWT token and return the authenticated user."""
        ...

    @abc.abstractmethod
    async def get_public_keys(self) -> dict:
        """Fetch JWKS public keys from the identity provider."""
        ...

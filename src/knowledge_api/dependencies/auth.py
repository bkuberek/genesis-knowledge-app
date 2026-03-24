from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from knowledge_core.domain.user import User  # noqa: TCH001
from knowledge_core.ports.auth_port import AuthPort  # noqa: TCH001

_auth_adapter: AuthPort | None = None

security = HTTPBearer(auto_error=False)


def set_auth_adapter(adapter: AuthPort) -> None:
    """Configure the auth adapter for dependency injection."""
    global _auth_adapter  # noqa: PLW0603
    _auth_adapter = adapter


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),  # noqa: B008
) -> User:
    """FastAPI dependency: validate JWT and return current user."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if _auth_adapter is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured",
        )

    try:
        return await _auth_adapter.validate_token(credentials.credentials)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

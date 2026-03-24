"""FastAPI dependency injection utilities."""

from knowledge_api.dependencies.auth import get_current_user, set_auth_adapter
from knowledge_api.dependencies.websocket_auth import authenticate_websocket

__all__ = [
    "authenticate_websocket",
    "get_current_user",
    "set_auth_adapter",
]

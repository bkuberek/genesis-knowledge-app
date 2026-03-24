"""FastAPI dependency injection utilities."""

from knowledge_api.dependencies.auth import get_current_user, set_auth_adapter
from knowledge_api.dependencies.container import Container, container
from knowledge_api.dependencies.websocket_auth import authenticate_websocket

__all__ = [
    "Container",
    "authenticate_websocket",
    "container",
    "get_current_user",
    "set_auth_adapter",
]

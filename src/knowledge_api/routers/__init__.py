"""API routers for the Knowledge application."""

from knowledge_api.routers.chat_router import router as chat_router
from knowledge_api.routers.documents_router import router as documents_router
from knowledge_api.routers.graph_router import router as graph_router
from knowledge_api.routers.websocket_handler import router as websocket_router

__all__ = [
    "chat_router",
    "documents_router",
    "graph_router",
    "websocket_router",
]

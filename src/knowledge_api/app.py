import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from knowledge_api.dependencies.auth import set_auth_adapter
from knowledge_api.dependencies.container import container
from knowledge_core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://localhost:8000"


def _get_allowed_origins() -> list[str]:
    """Return CORS origins from settings, falling back to development defaults."""
    raw = getattr(settings, "cors_origins", "") or DEFAULT_CORS_ORIGINS
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


MCP_TOOL_OPERATIONS = [
    "search_knowledge",
    "add_knowledge",
    "get_entity",
    "get_document_entities",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown hooks."""
    await container.initialize()
    set_auth_adapter(container.auth_adapter)
    yield
    await container.shutdown()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Knowledge",
        description=("Multi-user knowledge management with LLM-powered entity extraction"),
        version="0.1.0",
        lifespan=lifespan,
    )

    allowed_origins = _get_allowed_origins()
    logger.info("CORS allowed origins: %s", allowed_origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    async def health_check() -> dict:
        return {"status": "healthy"}

    _register_routers(app)
    _mount_mcp(app)
    _mount_frontend(app)

    return app


def _register_routers(app: FastAPI) -> None:
    """Register all API routers under the /api prefix."""
    from knowledge_api.routers.chat_router import router as chat_router
    from knowledge_api.routers.documents_router import (
        router as documents_router,
    )
    from knowledge_api.routers.graph_router import router as graph_router
    from knowledge_api.routers.websocket_handler import (
        router as ws_router,
    )

    app.include_router(documents_router, prefix="/api")
    app.include_router(graph_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(ws_router)


def _mount_mcp(app: FastAPI) -> None:
    """Mount MCP server exposing selected operations as tools."""
    try:
        from fastapi_mcp import FastApiMCP

        mcp = FastApiMCP(
            app,
            name="Knowledge MCP",
            description="Knowledge management tools",
            include_operations=MCP_TOOL_OPERATIONS,
        )
        mcp.mount_http()
        logger.info("MCP server mounted at /mcp")
    except Exception:
        logger.warning(
            "Failed to mount MCP server — fastapi-mcp may not be installed",
            exc_info=True,
        )


def _resolve_frontend_dir() -> str | None:
    """Find the frontend dist directory, checking multiple locations."""
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "frontend", "dist"),
        os.path.join(os.getcwd(), "frontend", "dist"),
    ]
    for candidate in candidates:
        normalized = os.path.normpath(candidate)
        if os.path.isdir(normalized):
            return normalized
    return None


def _mount_frontend(app: FastAPI) -> None:
    """Serve the frontend SPA if the build directory exists."""
    frontend_dir = _resolve_frontend_dir()
    if frontend_dir is None:
        return

    assets_dir = os.path.join(frontend_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount(
            "/assets",
            StaticFiles(directory=assets_dir),
            name="assets",
        )

    @app.get("/{path:path}", include_in_schema=False)
    async def serve_spa(path: str) -> FileResponse:
        file_path = os.path.join(frontend_dir, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dir, "index.html"))

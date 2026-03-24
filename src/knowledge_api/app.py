import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from knowledge_api.dependencies.auth import set_auth_adapter
from knowledge_api.dependencies.container import container

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:8000",
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    async def health_check() -> dict:
        return {"status": "healthy"}

    _register_routers(app)
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


def _mount_frontend(app: FastAPI) -> None:
    """Serve the frontend SPA if the build directory exists."""
    frontend_dir = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "frontend",
        "dist",
    )
    if not os.path.exists(frontend_dir):
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

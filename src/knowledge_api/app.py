from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown hooks."""
    # Startup: wire DI container, connect to database, etc.
    yield
    # Shutdown: close connections, cleanup resources


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Knowledge",
        description="Multi-user knowledge management with LLM-powered entity extraction",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health", tags=["system"])
    async def health_check() -> dict:
        return {"status": "healthy"}

    return app

import cyclopts
import uvicorn

app = cyclopts.App(name="knowledge", help="Knowledge Management CLI")


@app.command
def serve(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
) -> None:
    """Start the Knowledge API server."""
    uvicorn.run(
        "knowledge_api.app:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )


@app.command
def version() -> None:
    """Show the application version."""
    print("Knowledge v0.1.0")


if __name__ == "__main__":
    app()

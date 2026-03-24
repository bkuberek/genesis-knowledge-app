import pytest
from fastapi.testclient import TestClient

from knowledge_api.app import create_app


@pytest.fixture
def app():
    """Create a test application instance."""
    return create_app()


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)

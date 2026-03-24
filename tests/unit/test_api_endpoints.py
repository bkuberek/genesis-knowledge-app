"""Tests for REST API endpoints — auth enforcement and response structure."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from knowledge_api.app import create_app
from knowledge_api.dependencies.container import Container


@pytest.fixture
def app():
    """Create a fresh test app without running lifespan (no real DB)."""
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Health endpoint (no auth required)
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_returns_healthy(self, client):
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


# ---------------------------------------------------------------------------
# Auth enforcement — all API endpoints require a Bearer token
# ---------------------------------------------------------------------------


class TestDocumentEndpointsRequireAuth:
    def test_upload_document_requires_auth(self, client):
        response = client.post(
            "/api/documents",
            files={"file": ("test.txt", b"hello", "text/plain")},
        )

        assert response.status_code == 401

    def test_upload_url_requires_auth(self, client):
        response = client.post(
            "/api/documents/url",
            json={"url": "https://example.com"},
        )

        assert response.status_code == 401

    def test_list_documents_requires_auth(self, client):
        response = client.get("/api/documents")

        assert response.status_code == 401

    def test_get_document_requires_auth(self, client):
        doc_id = uuid.uuid4()
        response = client.get(f"/api/documents/{doc_id}")

        assert response.status_code == 401

    def test_get_document_entities_requires_auth(self, client):
        doc_id = uuid.uuid4()
        response = client.get(f"/api/documents/{doc_id}/entities")

        assert response.status_code == 401


class TestGraphEndpointsRequireAuth:
    def test_search_knowledge_requires_auth(self, client):
        response = client.get("/api/graph/search?q=test")

        assert response.status_code == 401

    def test_get_entity_requires_auth(self, client):
        entity_id = uuid.uuid4()
        response = client.get(f"/api/graph/entities/{entity_id}")

        assert response.status_code == 401

    def test_get_entity_relationships_requires_auth(self, client):
        entity_id = uuid.uuid4()
        response = client.get(
            f"/api/graph/entities/{entity_id}/relationships",
        )

        assert response.status_code == 401

    def test_add_knowledge_requires_auth(self, client):
        response = client.post(
            "/api/graph/knowledge",
            json={"text": "Some knowledge", "source": "test"},
        )

        assert response.status_code == 401


class TestChatEndpointsRequireAuth:
    def test_create_session_requires_auth(self, client):
        response = client.post(
            "/api/chat/sessions",
            json={"title": "Test"},
        )

        assert response.status_code == 401

    def test_list_sessions_requires_auth(self, client):
        response = client.get("/api/chat/sessions")

        assert response.status_code == 401

    def test_get_session_requires_auth(self, client):
        session_id = uuid.uuid4()
        response = client.get(f"/api/chat/sessions/{session_id}")

        assert response.status_code == 401

    def test_update_session_requires_auth(self, client):
        session_id = uuid.uuid4()
        response = client.patch(
            f"/api/chat/sessions/{session_id}",
            json={"title": "Updated"},
        )

        assert response.status_code == 401

    def test_delete_session_requires_auth(self, client):
        session_id = uuid.uuid4()
        response = client.delete(f"/api/chat/sessions/{session_id}")

        assert response.status_code == 401

    def test_get_messages_requires_auth(self, client):
        session_id = uuid.uuid4()
        response = client.get(f"/api/chat/sessions/{session_id}/messages")

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Container initialization
# ---------------------------------------------------------------------------


class TestContainer:
    def test_container_starts_uninitialized(self):
        c = Container()

        assert c.engine is None
        assert c.session_factory is None
        assert c.repository is None
        assert c.auth_adapter is None
        assert c.llm_client is None
        assert c.ingestion_pipeline is None

    @patch("knowledge_api.dependencies.container.create_engine")
    @patch("knowledge_api.dependencies.container.create_session_factory")
    @patch("knowledge_api.dependencies.container.DatabaseRepository")
    @patch("knowledge_api.dependencies.container.KeycloakAuthAdapter")
    @patch("knowledge_api.dependencies.container.LLMClient")
    @patch("knowledge_api.dependencies.container.FileDocumentStorage")
    @patch("knowledge_api.dependencies.container.IngestionPipeline")
    async def test_initialize_wires_all_dependencies(
        self,
        mock_pipeline,
        mock_storage,
        mock_llm,
        mock_auth,
        mock_repo,
        mock_session_factory,
        mock_engine,
    ):
        c = Container()
        await c.initialize()

        assert c.engine is not None
        assert c.session_factory is not None
        assert c.repository is not None
        assert c.auth_adapter is not None
        assert c.llm_client is not None
        assert c.ingestion_pipeline is not None
        mock_engine.assert_called_once()
        mock_session_factory.assert_called_once()

    async def test_shutdown_disposes_engine(self):
        c = Container()
        c.engine = AsyncMock()

        await c.shutdown()

        c.engine.dispose.assert_awaited_once()

    async def test_shutdown_without_engine_is_safe(self):
        c = Container()

        await c.shutdown()  # Should not raise

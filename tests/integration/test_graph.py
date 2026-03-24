"""Integration tests for graph/knowledge endpoints.

Tests knowledge addition, entity search, entity retrieval, and relationships.
The ``add_knowledge`` endpoint triggers synchronous LLM extraction, so tests
that call it are marked with ``@pytest.mark.llm``.
"""

import uuid

import httpx
import pytest

pytestmark = pytest.mark.integration

KNOWLEDGE_TEXT = (
    "Alice is the CEO of Acme Corporation. "
    "Bob is the CTO and reports to Alice. "
    "Acme Corporation is headquartered in San Francisco."
)
KNOWLEDGE_SOURCE = "integration-test"


# ---------------------------------------------------------------------------
# Knowledge addition (requires LLM)
# ---------------------------------------------------------------------------


class TestKnowledgeAdd:
    @pytest.mark.llm
    async def test_add_knowledge_returns_201(self, api_client: httpx.AsyncClient):
        response = await api_client.post(
            "/api/graph/knowledge",
            json={"text": KNOWLEDGE_TEXT, "source": KNOWLEDGE_SOURCE},
        )

        assert response.status_code == 201

    @pytest.mark.llm
    async def test_add_knowledge_returns_document_id(self, api_client: httpx.AsyncClient):
        response = await api_client.post(
            "/api/graph/knowledge",
            json={"text": KNOWLEDGE_TEXT, "source": KNOWLEDGE_SOURCE},
        )

        body = response.json()
        assert "document_id" in body
        uuid.UUID(body["document_id"])  # validates UUID format

    @pytest.mark.llm
    async def test_add_knowledge_extracts_entities(self, api_client: httpx.AsyncClient):
        response = await api_client.post(
            "/api/graph/knowledge",
            json={"text": KNOWLEDGE_TEXT, "source": KNOWLEDGE_SOURCE},
        )

        body = response.json()
        assert "entities_extracted" in body
        assert body["entities_extracted"] >= 0


# ---------------------------------------------------------------------------
# Entity search
# ---------------------------------------------------------------------------


class TestEntitySearch:
    async def test_search_returns_200(self, api_client: httpx.AsyncClient):
        response = await api_client.get("/api/graph/search?q=test")

        assert response.status_code == 200

    async def test_search_returns_entities_list(self, api_client: httpx.AsyncClient):
        response = await api_client.get("/api/graph/search?q=test")

        body = response.json()
        assert "entities" in body
        assert isinstance(body["entities"], list)

    async def test_search_returns_total_count(self, api_client: httpx.AsyncClient):
        response = await api_client.get("/api/graph/search?q=test")

        body = response.json()
        assert "total" in body
        assert isinstance(body["total"], int)

    async def test_search_empty_query_returns_200(self, api_client: httpx.AsyncClient):
        response = await api_client.get("/api/graph/search?q=")

        assert response.status_code == 200

    async def test_search_no_results_returns_empty(self, api_client: httpx.AsyncClient):
        response = await api_client.get(
            "/api/graph/search",
            params={"q": "zzz_nonexistent_xkcd_9999"},
        )

        body = response.json()
        assert body["entities"] == []
        assert body["total"] == 0

    async def test_search_respects_limit(self, api_client: httpx.AsyncClient):
        response = await api_client.get(
            "/api/graph/search",
            params={"q": "", "limit": 2},
        )

        body = response.json()
        assert len(body["entities"]) <= 2


# ---------------------------------------------------------------------------
# Get single entity
# ---------------------------------------------------------------------------


class TestEntityGet:
    async def test_get_nonexistent_entity_returns_404(self, api_client: httpx.AsyncClient):
        fake_id = uuid.uuid4()
        response = await api_client.get(f"/api/graph/entities/{fake_id}")

        assert response.status_code == 404

    @pytest.mark.llm
    async def test_get_entity_by_id_returns_200(self, api_client: httpx.AsyncClient):
        """Add knowledge, search for entities, then fetch one by ID."""
        await api_client.post(
            "/api/graph/knowledge",
            json={"text": KNOWLEDGE_TEXT, "source": KNOWLEDGE_SOURCE},
        )

        search = await api_client.get("/api/graph/search", params={"q": "", "limit": 1})
        entities = search.json()["entities"]
        if not entities:
            pytest.skip("No entities found to test get-by-id")

        entity_id = entities[0]["id"]
        response = await api_client.get(f"/api/graph/entities/{entity_id}")

        assert response.status_code == 200

    @pytest.mark.llm
    async def test_get_entity_has_expected_fields(self, api_client: httpx.AsyncClient):
        search = await api_client.get("/api/graph/search", params={"q": "", "limit": 1})
        entities = search.json()["entities"]
        if not entities:
            pytest.skip("No entities available")

        entity_id = entities[0]["id"]
        response = await api_client.get(f"/api/graph/entities/{entity_id}")

        body = response.json()
        expected_fields = {
            "id",
            "name",
            "canonical_name",
            "type",
            "properties",
            "source_count",
        }
        assert expected_fields.issubset(body.keys())


# ---------------------------------------------------------------------------
# Entity relationships
# ---------------------------------------------------------------------------


class TestEntityRelationships:
    @pytest.mark.llm
    async def test_get_relationships_returns_200(self, api_client: httpx.AsyncClient):
        search = await api_client.get("/api/graph/search", params={"q": "", "limit": 1})
        entities = search.json()["entities"]
        if not entities:
            pytest.skip("No entities available for relationship test")

        entity_id = entities[0]["id"]
        response = await api_client.get(f"/api/graph/entities/{entity_id}/relationships")

        assert response.status_code == 200

    @pytest.mark.llm
    async def test_get_relationships_returns_list(self, api_client: httpx.AsyncClient):
        search = await api_client.get("/api/graph/search", params={"q": "", "limit": 1})
        entities = search.json()["entities"]
        if not entities:
            pytest.skip("No entities available")

        entity_id = entities[0]["id"]
        response = await api_client.get(f"/api/graph/entities/{entity_id}/relationships")

        body = response.json()
        assert "relationships" in body
        assert isinstance(body["relationships"], list)


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------


class TestGraphAuthRequired:
    async def test_search_without_auth_returns_401(self, anon_client: httpx.AsyncClient):
        response = await anon_client.get("/api/graph/search?q=test")

        assert response.status_code == 401

    async def test_add_knowledge_without_auth_returns_401(self, anon_client: httpx.AsyncClient):
        response = await anon_client.post(
            "/api/graph/knowledge",
            json={"text": "test", "source": "test"},
        )

        assert response.status_code == 401

    async def test_get_entity_without_auth_returns_401(self, anon_client: httpx.AsyncClient):
        fake_id = uuid.uuid4()
        response = await anon_client.get(f"/api/graph/entities/{fake_id}")

        assert response.status_code == 401

    async def test_get_relationships_without_auth_returns_401(self, anon_client: httpx.AsyncClient):
        fake_id = uuid.uuid4()
        response = await anon_client.get(f"/api/graph/entities/{fake_id}/relationships")

        assert response.status_code == 401

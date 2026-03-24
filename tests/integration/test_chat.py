"""Integration tests for chat session CRUD endpoints.

Tests the complete chat session lifecycle: create, list, get, update,
get messages, and delete.
"""

import uuid

import httpx
import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Session creation
# ---------------------------------------------------------------------------


class TestChatSessionCreate:
    async def test_create_session_returns_201(self, api_client: httpx.AsyncClient):
        response = await api_client.post(
            "/api/chat/sessions",
            json={},
        )

        assert response.status_code == 201

    async def test_create_session_returns_id(self, api_client: httpx.AsyncClient):
        response = await api_client.post(
            "/api/chat/sessions",
            json={},
        )

        body = response.json()
        assert "id" in body
        uuid.UUID(body["id"])

    async def test_create_session_default_title(self, api_client: httpx.AsyncClient):
        response = await api_client.post(
            "/api/chat/sessions",
            json={},
        )

        body = response.json()
        assert body["title"] == "New Chat"

    async def test_create_session_custom_title(self, api_client: httpx.AsyncClient):
        response = await api_client.post(
            "/api/chat/sessions",
            json={"title": "My Test Chat"},
        )

        body = response.json()
        assert body["title"] == "My Test Chat"

    async def test_create_session_has_timestamps(self, api_client: httpx.AsyncClient):
        response = await api_client.post(
            "/api/chat/sessions",
            json={},
        )

        body = response.json()
        assert "created_at" in body
        assert "updated_at" in body


# ---------------------------------------------------------------------------
# Session listing
# ---------------------------------------------------------------------------


class TestChatSessionList:
    async def test_list_sessions_returns_200(self, api_client: httpx.AsyncClient):
        response = await api_client.get("/api/chat/sessions")

        assert response.status_code == 200

    async def test_list_sessions_returns_array(self, api_client: httpx.AsyncClient):
        response = await api_client.get("/api/chat/sessions")

        body = response.json()
        assert isinstance(body, list)

    async def test_list_sessions_contains_created_session(self, api_client: httpx.AsyncClient):
        create = await api_client.post(
            "/api/chat/sessions",
            json={"title": "List Test Session"},
        )
        created_id = create.json()["id"]

        response = await api_client.get("/api/chat/sessions")

        session_ids = [s["id"] for s in response.json()]
        assert created_id in session_ids


# ---------------------------------------------------------------------------
# Get single session
# ---------------------------------------------------------------------------


class TestChatSessionGet:
    async def test_get_session_returns_200(self, api_client: httpx.AsyncClient):
        create = await api_client.post(
            "/api/chat/sessions",
            json={"title": "Get Test"},
        )
        session_id = create.json()["id"]

        response = await api_client.get(f"/api/chat/sessions/{session_id}")

        assert response.status_code == 200

    async def test_get_session_matches_created(self, api_client: httpx.AsyncClient):
        create = await api_client.post(
            "/api/chat/sessions",
            json={"title": "Match Test"},
        )
        created = create.json()

        response = await api_client.get(f"/api/chat/sessions/{created['id']}")

        body = response.json()
        assert body["id"] == created["id"]
        assert body["title"] == "Match Test"


# ---------------------------------------------------------------------------
# Update session
# ---------------------------------------------------------------------------


class TestChatSessionUpdate:
    async def test_update_session_returns_200(self, api_client: httpx.AsyncClient):
        create = await api_client.post(
            "/api/chat/sessions",
            json={"title": "Before Update"},
        )
        session_id = create.json()["id"]

        response = await api_client.patch(
            f"/api/chat/sessions/{session_id}",
            json={"title": "After Update"},
        )

        assert response.status_code == 200

    async def test_update_session_changes_title(self, api_client: httpx.AsyncClient):
        create = await api_client.post(
            "/api/chat/sessions",
            json={"title": "Original Title"},
        )
        session_id = create.json()["id"]

        await api_client.patch(
            f"/api/chat/sessions/{session_id}",
            json={"title": "Updated Title"},
        )

        get_response = await api_client.get(f"/api/chat/sessions/{session_id}")
        assert get_response.json()["title"] == "Updated Title"


# ---------------------------------------------------------------------------
# Session messages
# ---------------------------------------------------------------------------


class TestChatSessionMessages:
    async def test_get_messages_returns_200(self, api_client: httpx.AsyncClient):
        create = await api_client.post(
            "/api/chat/sessions",
            json={},
        )
        session_id = create.json()["id"]

        response = await api_client.get(f"/api/chat/sessions/{session_id}/messages")

        assert response.status_code == 200

    async def test_new_session_has_no_messages(self, api_client: httpx.AsyncClient):
        create = await api_client.post(
            "/api/chat/sessions",
            json={},
        )
        session_id = create.json()["id"]

        response = await api_client.get(f"/api/chat/sessions/{session_id}/messages")

        body = response.json()
        assert body == []


# ---------------------------------------------------------------------------
# Delete session
# ---------------------------------------------------------------------------


class TestChatSessionDelete:
    async def test_delete_session_returns_204(self, api_client: httpx.AsyncClient):
        create = await api_client.post(
            "/api/chat/sessions",
            json={"title": "To Delete"},
        )
        session_id = create.json()["id"]

        response = await api_client.delete(f"/api/chat/sessions/{session_id}")

        assert response.status_code == 204

    async def test_get_deleted_session_returns_404(self, api_client: httpx.AsyncClient):
        create = await api_client.post(
            "/api/chat/sessions",
            json={"title": "Delete Then Get"},
        )
        session_id = create.json()["id"]

        await api_client.delete(f"/api/chat/sessions/{session_id}")

        response = await api_client.get(f"/api/chat/sessions/{session_id}")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestChatErrors:
    async def test_get_nonexistent_session_returns_404(self, api_client: httpx.AsyncClient):
        fake_id = uuid.uuid4()
        response = await api_client.get(f"/api/chat/sessions/{fake_id}")

        assert response.status_code == 404

    async def test_create_session_without_auth_returns_401(self, anon_client: httpx.AsyncClient):
        response = await anon_client.post(
            "/api/chat/sessions",
            json={"title": "No Auth"},
        )

        assert response.status_code == 401

    async def test_list_sessions_without_auth_returns_401(self, anon_client: httpx.AsyncClient):
        response = await anon_client.get("/api/chat/sessions")

        assert response.status_code == 401

    async def test_get_session_without_auth_returns_401(self, anon_client: httpx.AsyncClient):
        fake_id = uuid.uuid4()
        response = await anon_client.get(f"/api/chat/sessions/{fake_id}")

        assert response.status_code == 401

    async def test_update_session_without_auth_returns_401(self, anon_client: httpx.AsyncClient):
        fake_id = uuid.uuid4()
        response = await anon_client.patch(
            f"/api/chat/sessions/{fake_id}",
            json={"title": "No Auth"},
        )

        assert response.status_code == 401

    async def test_delete_session_without_auth_returns_401(self, anon_client: httpx.AsyncClient):
        fake_id = uuid.uuid4()
        response = await anon_client.delete(f"/api/chat/sessions/{fake_id}")

        assert response.status_code == 401

    async def test_get_messages_without_auth_returns_401(self, anon_client: httpx.AsyncClient):
        fake_id = uuid.uuid4()
        response = await anon_client.get(f"/api/chat/sessions/{fake_id}/messages")

        assert response.status_code == 401

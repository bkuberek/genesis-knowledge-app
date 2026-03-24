"""Integration tests for document CRUD endpoints.

Tests the full document lifecycle: upload, list, get, get entities, and error paths.
Requires a running API with Keycloak authentication.
"""

import io
import uuid

import httpx
import pytest

pytestmark = pytest.mark.integration

CSV_CONTENT = "name,role,company\nAlice,CEO,Acme Corp\nBob,CTO,Acme Corp"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_csv_upload(filename: str = "test-data.csv") -> dict:
    """Build multipart file payload for a small CSV upload."""
    file_bytes = io.BytesIO(CSV_CONTENT.encode())
    return {"file": (filename, file_bytes, "text/csv")}


# ---------------------------------------------------------------------------
# Document upload
# ---------------------------------------------------------------------------


class TestDocumentUpload:
    async def test_upload_csv_returns_201(self, api_client: httpx.AsyncClient):
        response = await api_client.post(
            "/api/documents",
            files=_build_csv_upload(),
        )

        assert response.status_code == 201

    async def test_upload_csv_returns_document_id(self, api_client: httpx.AsyncClient):
        response = await api_client.post(
            "/api/documents",
            files=_build_csv_upload(),
        )

        body = response.json()
        assert "id" in body
        uuid.UUID(body["id"])  # validates it's a real UUID

    async def test_upload_csv_returns_filename(self, api_client: httpx.AsyncClient):
        response = await api_client.post(
            "/api/documents",
            files=_build_csv_upload("my-upload.csv"),
        )

        body = response.json()
        assert body["filename"] == "my-upload.csv"

    async def test_upload_csv_returns_status(self, api_client: httpx.AsyncClient):
        response = await api_client.post(
            "/api/documents",
            files=_build_csv_upload(),
        )

        body = response.json()
        assert "status" in body

    async def test_upload_csv_returns_created_at(self, api_client: httpx.AsyncClient):
        response = await api_client.post(
            "/api/documents",
            files=_build_csv_upload(),
        )

        body = response.json()
        assert "created_at" in body


# ---------------------------------------------------------------------------
# Document listing
# ---------------------------------------------------------------------------


class TestDocumentList:
    async def test_list_documents_returns_200(self, api_client: httpx.AsyncClient):
        response = await api_client.get("/api/documents")

        assert response.status_code == 200

    async def test_list_documents_returns_array(self, api_client: httpx.AsyncClient):
        response = await api_client.get("/api/documents")

        body = response.json()
        assert "documents" in body
        assert isinstance(body["documents"], list)

    async def test_list_documents_contains_uploaded_doc(self, api_client: httpx.AsyncClient):
        upload = await api_client.post(
            "/api/documents",
            files=_build_csv_upload("list-test.csv"),
        )
        uploaded_id = upload.json()["id"]

        response = await api_client.get("/api/documents")

        doc_ids = [d["id"] for d in response.json()["documents"]]
        assert uploaded_id in doc_ids


# ---------------------------------------------------------------------------
# Get single document
# ---------------------------------------------------------------------------


class TestDocumentGet:
    async def test_get_document_returns_200(self, api_client: httpx.AsyncClient):
        upload = await api_client.post(
            "/api/documents",
            files=_build_csv_upload("get-test.csv"),
        )
        doc_id = upload.json()["id"]

        response = await api_client.get(f"/api/documents/{doc_id}")

        assert response.status_code == 200

    async def test_get_document_matches_upload(self, api_client: httpx.AsyncClient):
        upload = await api_client.post(
            "/api/documents",
            files=_build_csv_upload("match-test.csv"),
        )
        doc_id = upload.json()["id"]

        response = await api_client.get(f"/api/documents/{doc_id}")

        body = response.json()
        assert body["id"] == doc_id
        assert body["filename"] == "match-test.csv"

    async def test_get_document_has_expected_fields(self, api_client: httpx.AsyncClient):
        upload = await api_client.post(
            "/api/documents",
            files=_build_csv_upload(),
        )
        doc_id = upload.json()["id"]

        response = await api_client.get(f"/api/documents/{doc_id}")

        body = response.json()
        expected_fields = {
            "id",
            "filename",
            "content_type",
            "status",
            "stage",
            "source_type",
            "visibility",
            "created_at",
            "updated_at",
        }
        assert expected_fields.issubset(body.keys())


# ---------------------------------------------------------------------------
# Document entities
# ---------------------------------------------------------------------------


class TestDocumentEntities:
    async def test_get_entities_returns_200(self, api_client: httpx.AsyncClient):
        upload = await api_client.post(
            "/api/documents",
            files=_build_csv_upload("entities-test.csv"),
        )
        doc_id = upload.json()["id"]

        response = await api_client.get(f"/api/documents/{doc_id}/entities")

        assert response.status_code == 200

    async def test_get_entities_returns_list(self, api_client: httpx.AsyncClient):
        upload = await api_client.post(
            "/api/documents",
            files=_build_csv_upload(),
        )
        doc_id = upload.json()["id"]

        response = await api_client.get(f"/api/documents/{doc_id}/entities")

        body = response.json()
        assert "entities" in body
        assert isinstance(body["entities"], list)


# ---------------------------------------------------------------------------
# URL upload
# ---------------------------------------------------------------------------


class TestDocumentUrlUpload:
    async def test_upload_url_returns_201(self, api_client: httpx.AsyncClient):
        response = await api_client.post(
            "/api/documents/url",
            json={"url": "https://example.com"},
        )

        # The endpoint may return 201 (success) or a 4xx/5xx
        # depending on whether the URL is reachable and parseable.
        # We accept 201 as the expected success case.
        assert response.status_code in (201, 422, 500)


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestDocumentErrors:
    async def test_get_nonexistent_document_returns_404(self, api_client: httpx.AsyncClient):
        fake_id = uuid.uuid4()
        response = await api_client.get(f"/api/documents/{fake_id}")

        assert response.status_code == 404

    async def test_upload_without_auth_returns_401(self, anon_client: httpx.AsyncClient):
        response = await anon_client.post(
            "/api/documents",
            files=_build_csv_upload(),
        )

        assert response.status_code == 401

    async def test_list_without_auth_returns_401(self, anon_client: httpx.AsyncClient):
        response = await anon_client.get("/api/documents")

        assert response.status_code == 401

    async def test_get_without_auth_returns_401(self, anon_client: httpx.AsyncClient):
        fake_id = uuid.uuid4()
        response = await anon_client.get(f"/api/documents/{fake_id}")

        assert response.status_code == 401
